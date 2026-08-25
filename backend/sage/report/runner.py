"""Report 실행기 — plan DAG codegen + TaskContext 실행.

전체 파이프라인 (보고서 생성):
  1. routers.report.handle_report_generation
  2. nodes/report/plan → ReportPlanOutput (tasks[].context 가 DAG edge)
  3. iter_plan_tasks → 태스크별 codegen_task → reports/{rid}/srcs/{task_id}.py
  4. run_task → run_task_code → sage/exec (docker_pool) → worker run_task
  5. collect_report_result → report.json / draft.json / context.json

재실행 (publish 후):
  - iter_report_exec: codegen 없이 srcs/*.py 만 DAG 병렬 실행
  - 결과·로그는 reports/ 가 아닌 runs/run-YYYYMMDD-HHMM/ 에 격리

병렬·SSE:
  - 의존성 없는 태스크는 _iter_tasks_parallel 워커로 동시 실행
  - _ParallelEventMux 가 태스크별 큐를 병합할 때 executing/progress 를
    generating/waiting 보다 우선 내보내 UI 이벤트 역전을 완화

재시도 계층 (generate 경로):
  A. NodeV 내부 max_retries — LLM 출력 Pydantic/validator 실패 (같은 요청)
  B. MAX_TASK_SOURCE_RETRIES — 생성 task 소스 실행·contract 오류 재호출
     (exec worker·pool 인프라 오류 / 연결 오류 → 재생성 없음)
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import traceback
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

import cfg
from sage.report.context import TaskContext
from sage.report.exec_errors import ExecPlatformError, is_exec_platform_error
from sage.errs import (
    MaxRetriesExceededError,
    CodegenContractError,
    QuotaExceededError,
    LLMTimeoutError,
    ContextAttachTooLargeError,
    ContextStorageError,
    is_quota_error,
)
from sage.logg import error, info, warning
from sage.models.node import PlanTask, ReportPlanOutput, TaskOutput, TaskRun
from sage.report.plan_tools import resolve_task_tool_paths
from sage.report.task_codegen import get_task_node
from sage.report.task_sources import (
    REPORTS_DIR,
    ensure_report_dirs,
    report_dir,
    report_srcs_dir,
    save_task_source,
    task_source_path,
)

# nodes/report/task/{data,analyze,...} — TaskCodegenNode instruction 루트
TASK_ROOT = Path(cfg.root_path) / "nodes" / "report" / "task"
# 일회성 실행 산출: logs/, run_meta.json (rid 와 물리적으로 분리)
RUNS_DIR = Path(cfg.root_path) / "runs"

# SSE progress / reporter 메시지에 쓰는 유형별 한 줄 설명 (UI 한글)
TASK_TYPE_INTRO = {
    "data": "데이터셋 로드 → 만료 필드 확인 → 외부 API 수집 → parquet 갱신",
    "analyze": "upstream 결과 로드 → 지표·집계 계산",
    "visual": "차트·표 데이터 생성",
    "narrative": "분석 결과 기반 서술 작성",
    "release": "리포트 레이아웃·문서 조립",
}

# codegen 성공 후 실행이 깨지면 traceback 을 붙여 소스 재생성 — NodeV.max_retries 와 별개
MAX_TASK_SOURCE_RETRIES = 3


def safe_report(reporter, message: str, state: str = "running") -> None:
    """run_task 내부 진행 보고 — 반드시 동기(await 금지).

    LLM 이 ``await reporter.update(...)`` 를 생성하면 unify/runner 가 깨진다.
    TaskReporter.update → Queue.put_nowait 로 메인 이벤트 루프의 drain 루프가
    SSE ``progress`` 로 내보낸다. reporter 가 없으면 sage.logg 로 fallback.
    """
    if reporter and hasattr(reporter, "update"):
        try:
            reporter.update(message, state=state)
            return
        except Exception:
            # reporter 장애가 태스크 전체를 죽이면 안 됨 — 로그만 남김
            pass
    if state == "failed":
        error(message)
    elif state == "completed":
        info(message)
    else:
        info(message)


# MCP/stdio/HTTP 끊김에 자주 등장하는 문자열
# 연결 오류는 소스 재생성이 아니라 인프라 재시도가 맞으므로 codegen 루프에서 제외한다.
_CONNECTION_MARKERS = (
    "connection",
    "timeout",
    "timed out",
    "fastmcp",
    "연결 실패",
    "closedresource",
    "10054",  # WinError — TCP 강제 종료
    "socket",
    "connect",
    "refused",
    "service unavailable",
    "unavailable",
    "broken pipe",
    "reset by peer",
)


class TaskReporter:
    """진행 메시지 수집기 — pangeaze unify 와 report run_task 가 공유.

    설계:
      - update() 는 async 가 아님 → unify.py / 생성 소스가 await 하지 않음
      - put_nowait 로 큐잉 → _iter_one_plan_task 의 폴링 drain 이 SSE 로 변환
      - status 필드는 마지막 state 스냅샷 (failed/completed/running)
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self.status = "running"

    def update(self, message: str, state: str = "running") -> None:
        from sage.text import nfc_user_text

        message = nfc_user_text(message)
        self.status = state
        self._queue.put_nowait(message)
        if state == "failed":
            error(message)
        elif state == "completed":
            info(message)
        else:
            info(message)

    def drain(self) -> list[str]:
        """논블로킹으로 큐를 비움 — SSE progress 배치 전송용."""
        msgs: list[str] = []
        while not self._queue.empty():
            try:
                msgs.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return msgs

    async def iter_while(self, task: asyncio.Task, *, poll_sec: float = 0.05):
        """exec task 완료까지 drain — report/pangea/tool SSE 공통."""
        while not task.done():
            for msg in self.drain():
                yield msg
            await asyncio.sleep(poll_sec)
        for msg in self.drain():
            yield msg


# LLM 이 unify_data 안에서 await reporter.update 를 쓰는 흔한 패턴을 정적 교정
_UNIFY_REPORTER_AWAIT_RE = re.compile(r"\bawait\s+reporter\.update\s*\(")


def normalize_unify_reporter_calls(code: str) -> str:
    """unify.py 저장 직전 — ``await reporter.update(`` → ``reporter.update(``.

    TaskReporter.update 는 동기인데 LLM 이 async API 로 오해하는 경우가 많다.
    이 정규식 치환을 건너뛰면 unify 실행이 TypeError 로 실패한다.
    """
    return _UNIFY_REPORTER_AWAIT_RE.sub("reporter.update(", code)


class RunTaskLog:
    """published exec 전용 — runs/{run_id}/logs/{task_id}.log 에 append.

    generate 경로의 콘솔/report 로그와 분리해, 동일 rid 를 여러 번 exec 해도
    실행별 로그가 덮어쓰이지 않도록 한다.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, line: str) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")

    def write(self, content: str) -> None:
        self.path.write_text(content.rstrip() + "\n", encoding="utf-8")


class RunTaskReporter(TaskReporter):
    """TaskReporter + 파일 로그 — exec 경로에서 SSE 와 디스크를 동시에 남김."""

    def __init__(self, log: RunTaskLog) -> None:
        super().__init__()
        self._log = log

    def update(self, message: str, state: str = "running") -> None:
        super().update(message, state)
        self._log.append(f"[{state}] {message}")


# ---------------------------------------------------------------------------
# 보고서 디스크 레이아웃 — sage.report.task_sources (exec worker 와 공유)
# ---------------------------------------------------------------------------


def task_context_for_report(
    rid: str,
    plan_id: str,
    *,
    plan_task_ids: list[str] | None = None,
) -> TaskContext:
    """TaskContext 로드 — 칠판은 dump/{hex}/ 에, 소스는 reports/{rid}/ 에.

    ``plan_task_ids`` 로 plan에 없는 stale task 를 걸러 llm_attach 오염을 방지한다.
    update/generate 가 같은 plan_id·rid 를 쓰면 칠판을 유지한다.
    """
    ensure_report_dirs(rid)
    ctx = TaskContext.load(plan_id, rid=rid, plan_task_ids=plan_task_ids)
    ctx.rid = rid
    return ctx


def apply_upstream_source_updates(rid: str, updates: dict[str, str]) -> dict[str, str]:
    """Release QA 가 upstream srcs 를 고친 최종본으로 덮어쓴다.

    초안/버전 파일이 없다 — 한 번 쓰면 이전 .py 는 복구 불가.
    ``task_shell.assemble_task_source`` + ``validate_task_code`` 를 거친 뒤에만 저장한다.

    release codegen 에서는 ``apply_upstream_patches`` 사용 — 전체 embed 금지.
    """
    from sage.report.upstream_sources import persist_task_body

    if not updates:
        raise ValueError("apply_upstream_source_updates: updates 가 비어 있습니다.")
    saved: dict[str, str] = {}
    for task_id, code in updates.items():
        if not task_id.startswith("task-"):
            raise ValueError(f"apply_upstream_source_updates: invalid task_id {task_id!r}")
        if not code or not code.strip():
            raise ValueError(f"apply_upstream_source_updates: {task_id} 소스가 비어 있습니다.")
        from sage.report.task_shell import extract_task_body

        body = extract_task_body(code)
        saved[task_id] = persist_task_body(rid, task_id, body, validate="full")
    return saved


def save_plan(rid: str, plan: ReportPlanOutput | dict) -> Path:
    """plan blueprint JSON — exec/update 시 DB 보다 디스크를 우선 로드."""
    path = report_dir(rid) / "plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = plan if isinstance(plan, dict) else plan.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_report_artifact(rid: str, name: str, payload: Any) -> Path:
    """선택 산출물: reports/{rid}/{name}.json — draft, report, context 등."""
    return save_json_artifact(report_dir(rid) / f"{name}.json", payload)


def save_json_artifact(path: Path, payload: Any) -> Path:
    """임의 Path 에 JSON 저장 (runs/ 쪽 artifact 에도 재사용)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def make_run_dir() -> tuple[str, Path]:
    """같은 분에 두 번 exec 하면 run-YYYYMMDD-HHMM-1, -2 … 로 충돌 회피."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("run-%Y%m%d-%H%M")
    path = RUNS_DIR / stamp
    suffix = 0
    while path.exists():
        suffix += 1
        path = RUNS_DIR / f"{stamp}-{suffix}"
    path.mkdir(parents=True)
    (path / "logs").mkdir()
    return path.name, path


def load_plan_from_report(rid: str, *, db_plan: Any | None = None) -> ReportPlanOutput:
    """디스크 plan.json 우선 — generate 중 저장된 파일이 exec/update 의 진실.

    DB blueprint 는 파일 유실·수동 복구 시 fallback. 둘 다 없으면 FileNotFoundError.
    """
    plan_path = report_dir(rid) / "plan.json"
    if plan_path.is_file():
        return ReportPlanOutput.model_validate(
            json.loads(plan_path.read_text(encoding="utf-8"))
        )
    if db_plan is not None and getattr(db_plan, "blueprint", None):
        return ReportPlanOutput.model_validate(db_plan.blueprint)
    raise FileNotFoundError(f"plan.json 없음: {plan_path}")


def missing_task_sources(rid: str, plan: ReportPlanOutput) -> list[str]:
    """exec 전 검사 — srcs 가 빠진 task_id 목록 (빈 리스트면 준비 완료)."""
    return [
        t.task_id
        for t in plan.tasks
        if not task_source_path(rid, t.task_id).is_file()
    ]


def save_run_meta(
        run_dir: Path,
        *,
        run_id: str,
        rid: str,
        plan_id: str,
        status: str,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error: str | None = None,
) -> Path:
    """run_meta.json — UI/디버그용 실행 요약 (성공·실패 모두 기록)."""
    payload: dict[str, Any] = {
        "run_id": run_id,
        "rid": rid,
        "plan_id": plan_id,
        "status": status,
        "started_at": (started_at or datetime.now()).isoformat(),
    }
    if finished_at is not None:
        payload["finished_at"] = finished_at.isoformat()
    if error:
        payload["error"] = error
    return save_json_artifact(run_dir / "run_meta.json", payload)


def setup_task_paths() -> None:
    """생성 소스가 ``import sage...`` / 로컬 헬퍼를 찾을 수 있게 sys.path 보강.

    exec() 로 로드하는 모듈은 패키지 진입점이 아니므로 root 와 TASK_ROOT 를 삽입한다.
    """
    root = cfg.root_path
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(TASK_ROOT) not in sys.path:
        sys.path.insert(0, str(TASK_ROOT))


def topo_sort_tasks(tasks: list[PlanTask]) -> list[PlanTask]:
    """context[] 를 edge 로 보는 Kahn 위상정렬 — index 표시·문서화용.

    실제 병렬 실행은 _iter_tasks_parallel 의 asyncio.Event 게이트가 담당한다.
    순환·미정의 context 가 있으면 여기서 즉시 ValueError.
    """
    by_id = {t.task_id: t for t in tasks}
    if len(by_id) != len(tasks):
        raise ValueError("plan.tasks 에 중복 task_id 가 있습니다.")

    # tid → 아직 완료되지 않은 의존 집합
    pending = {t.task_id: set(t.context) for t in tasks}
    order: list[PlanTask] = []

    while pending:
        # 정렬하여 안정적·재현 가능한 순서
        ready = sorted(tid for tid, deps in pending.items() if not deps)
        if not ready:
            raise ValueError("plan.tasks DAG 에 순환 또는 누락된 context 가 있습니다.")
        for tid in ready:
            order.append(by_id[tid])
            del pending[tid]
        for deps in pending.values():
            deps.difference_update(ready)

    return order


def _plan_dict(plan: ReportPlanOutput | dict) -> dict:
    """노드/라우터에서 모델·dict 혼용을 허용하기 위한 정규화."""
    return plan if isinstance(plan, dict) else plan.model_dump()


def _task_dict(task: PlanTask | dict) -> dict:
    return task if isinstance(task, dict) else task.model_dump()


class TaskSourceError(Exception):
    """생성된 executor 소스 오류 — MAX_TASK_SOURCE_RETRIES 재생성 대상.

    연결/쿼터/타임아웃/ExecPlatformError 와는 구분한다.
    """


def validate_task_code(code: str, task_id: str = "") -> None:
    """저장 직전 정적 검증 — AST compile + run_task_code_validators.

    칠판(board)·타입 의존 validator 는 여기서 제외한다.
    그것들은 validate_codegen_output (async, tools/board 필요) 경로.
    """
    try:
        mod_name = f"p2_validate_{task_id.replace('-', '_')}" if task_id else "p2_validate"
        compile(code, f"<{mod_name}>", "exec")
    except SyntaxError as exc:
        raise TaskSourceError(f"SyntaxError: {exc}") from exc
    try:
        from sage.report.validators import run_task_code_validators

        run_task_code_validators(code)
    except ValueError as exc:
        raise TaskSourceError(str(exc)) from exc


def is_connection_error(exc: BaseException) -> bool:
    """MCP·소켓·타임아웃류 — 소스 재생성 대신 fail-fast."""
    if isinstance(
            exc,
            (
                    ConnectionError,
                    ConnectionResetError,
                    BrokenPipeError,
                    TimeoutError,
                    asyncio.TimeoutError,
            ),
    ):
        return True
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(marker in text for marker in _CONNECTION_MARKERS)


def is_mcp_call_error(exc: BaseException) -> bool:
    """호출 인자/스펙 불일치 — 코드를 고쳐야 하므로 source_error 로 분류."""
    msg = str(exc).lower()
    return (
            "unexpected keyword argument" in msg
            or "validation error for call[" in msg
            or ("pangea 도구 호출 실패" in msg and "validation error" in msg)
    )


def is_source_error(exc: BaseException) -> bool:
    """실행 중 오류가 codegen 재시도로 고칠 수 있는지 판별.

    - exec worker / docker pool → False (플랫폼)
    - 연결 오류 → False
    - 생성 task 소스 Syntax/Name/Type… → True
    """
    if isinstance(exc, ExecPlatformError):
        return False
    if is_connection_error(exc):
        return False
    if isinstance(exc, TaskSourceError) and is_exec_platform_error(str(exc)):
        return False
    if isinstance(
            exc,
            (
                    TaskSourceError,
                    SyntaxError,
                    IndentationError,
                    TabError,
                    NameError,
                    TypeError,
                    ValueError,
                    KeyError,
                    IndexError,
                    AttributeError,
                    ZeroDivisionError,
            ),
    ):
        return True
    # 동적 exec 모듈명(p2_exec_*) ImportError 는 로더 이슈일 수 있어 제외
    if isinstance(exc, ImportError) and "p2_exec_" not in str(exc):
        return True
    if isinstance(exc, RuntimeError) and is_mcp_call_error(exc):
        return True
    if isinstance(exc, RuntimeError) and "event loop is already running" in str(exc).lower():
        return False
    if isinstance(exc, Exception) and "PydanticUserError" in type(exc).__name__:
        return True
    msg = str(exc).lower()
    if "syntaxerror" in msg or "invalid syntax" in msg or "indentationerror" in msg:
        return True
    # 생성 executor 런타임 — 수정 가능한 오류로 간주
    return True


def downstream_task_closure(tasks: list[PlanTask], seed_ids: set[str]) -> set[str]:
    """report/update — 요청 task_ids + 전이적 downstream 을 한 집합으로.

    A→B→C 이고 A 만 요청해도 B,C 가 포함된다.
    upstream 이 바뀌면 칠판 key 가 달라질 수 있어 downstream 재 codegen/실행이 필수.
    """
    to_rerun = set(seed_ids)
    while True:
        added = False
        for task in tasks:
            if task.task_id in to_rerun:
                continue
            if any(dep in to_rerun for dep in task.context):
                to_rerun.add(task.task_id)
                added = True
        if not added:
            break
    return to_rerun


class _ParallelEventMux:
    """태스크별 이벤트 큐 + 위상 우선순위 merge.

    왜 필요한가:
      여러 worker 가 동시에 generating/executing/progress 를 produce 하면
      단순 asyncio.Queue 병합은 ``progress`` 뒤에 다른 태스크의 ``generating`` 이
      끼어 UI 타임라인 이 어긋난다.
      executing 중인 태스크 이벤트를 먼저 drain 해 체감 순서를 맞춘다.

    위상 순위(낮을수록 먼저):
      executing(0) < codegen(1) < waiting(2) < idle(3) < done(4)
    동일 순위는 round-robin(_rr)으로 공정성 유지.
    """

    _PHASE_RANK = {"executing": 0, "codegen": 1, "waiting": 2, "idle": 3, "done": 4}

    def __init__(self, task_ids: list[str]):
        self._queues = {tid: asyncio.Queue() for tid in task_ids}
        self._phase = {tid: "idle" for tid in task_ids}
        self._order = list(task_ids)
        self._rr = 0
        # publish 가 오면 get() 대기자를 깨움
        self._notify = asyncio.Event()

    def _rank(self, tid: str) -> int:
        return self._PHASE_RANK.get(self._phase[tid], 3)

    def _update_phase(self, tid: str, event: str) -> None:
        """SSE event 이름 → 내부 phase 상태머신."""
        if event == "waiting":
            self._phase[tid] = "waiting"
        elif event in ("generating", "retrying"):
            # 이미 실행 중이면 codegen 재시도로 phase 를 되돌리지 않음
            if self._phase[tid] != "executing":
                self._phase[tid] = "codegen"
        elif event == "executing":
            self._phase[tid] = "executing"
        elif event in ("executed", "failed"):
            self._phase[tid] = "done"

    async def publish(self, tid: str, ev: dict[str, Any]) -> None:
        await self._queues[tid].put(ev)
        self._update_phase(tid, ev.get("event", ""))
        self._notify.set()

    def _pick_tid(self) -> str | None:
        """비어 있지 않은 큐 중 최고 우선순위(+ RR) 태스크 선택."""
        n = len(self._order)
        if not n:
            return None
        best_rank = 999
        candidates: list[str] = []
        for i in range(n):
            tid = self._order[(self._rr + i) % n]
            if self._queues[tid].empty():
                continue
            rank = self._rank(tid)
            if rank < best_rank:
                best_rank = rank
                candidates = [tid]
            elif rank == best_rank:
                candidates.append(tid)
        if not candidates:
            return None
        tid = candidates[0]
        self._rr = (self._order.index(tid) + 1) % n
        return tid

    async def get(self, *, timeout: float = 0.05) -> dict[str, Any] | None:
        """즉시 꺼낼 이벤트가 없으면 notify+timeout 대기. 타임아웃 시 None."""
        tid = self._pick_tid()
        if tid is not None:
            return self._queues[tid].get_nowait()
        self._notify.clear()
        try:
            await asyncio.wait_for(self._notify.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        tid = self._pick_tid()
        if tid is None:
            return None
        return self._queues[tid].get_nowait()

    def empty(self) -> bool:
        return all(q.empty() for q in self._queues.values())


async def _iter_tasks_parallel(
        plan: ReportPlanOutput,
        *,
        rid: str,
        task_runner,
        only_tasks: set[str] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """DAG 병렬 실행 골격 — iter_plan_tasks / iter_report_exec 가 공유.

    메커니즘:
      1. task_id → asyncio.Event (완료 신호)
      2. worker 는 context[] Event 를 gather 로 기다린 뒤 task_runner 를 돌림
      3. 이벤트를 mux 에 publish → 이 함수가 merge 해 yield
      4. fail_exc 가 생기면 다른 worker 는 waiting 후 조기 return (fail-fast)
      5. only_tasks: update 부분 재생성 — 비대상 Event 를 미리 set 해 의존성 충족

    task_runner: async generator(PlanTask) → SSE dict
    """
    tasks = plan.tasks
    by_id = {t.task_id: t for t in tasks}
    # plan 이 깨진 dependency 를 가지고 있으면 시작 전에 실패
    for task in tasks:
        for dep in task.context:
            if dep not in by_id:
                raise ValueError(f"task {task.task_id} — context dep {dep!r} 없음")

    task_events = {t.task_id: asyncio.Event() for t in tasks}
    # only_tasks 지정 시: 대상 외 태스크는 이미 완료된 것처럼 취급
    # (upstream 이 only 밖에 있어도 waiting 이 영원히 걸리지 않음)
    if only_tasks is not None:
        for tid, event in task_events.items():
            if tid not in only_tasks:
                event.set()

    active_ids = [
        t.task_id for t in tasks
        if only_tasks is None or t.task_id in only_tasks
    ]
    mux = _ParallelEventMux(active_ids)
    # 첫 실패 예외만 보관 — finally 에서 재전파
    fail_exc: list[BaseException] = []

    async def worker(task: PlanTask) -> None:
        tid = task.task_id
        if only_tasks is not None and tid not in only_tasks:
            return
        try:
            if task.context:
                # upstream task_id 가 모두 executed 되면 asyncio.Event 로 깨움
                await mux.publish(tid, {
                    "event": "waiting",
                    "msg": f"[{task.title}] 이전 작업 완료 대기…",
                    "task_id": tid,
                    "task_type": task.type,
                    "rid": rid,
                })
                await asyncio.gather(
                    *(task_events[c].wait() for c in task.context if c in task_events)
                )
            # 대기 중 다른 worker 가 실패한 경우 — 불필요한 codegen/exec 스킵
            if fail_exc:
                return
            async for ev in task_runner(task):
                await mux.publish(tid, ev)
                if ev.get("event") == "failed":
                    err = ev.get("error") or ev.get("msg") or "task failed"
                    exc = TaskSourceError(str(err))
                    if not fail_exc:
                        fail_exc.append(exc)
                    raise exc
        except BaseException as exc:
            if not fail_exc:
                fail_exc.append(exc)
            raise
        finally:
            # 성공/실패와 무관하게 downstream 대기자를 깨움
            # (실패 시에도 DAG 가 영구 hang 되지 않도록)
            task_events[tid].set()

    workers = [asyncio.create_task(worker(t)) for t in tasks]

    try:
        while True:
            if all(w.done() for w in workers) and mux.empty():
                break
            item = await mux.get(timeout=0.05)
            if item is not None:
                yield item
    finally:
        worker_results = await asyncio.gather(*workers, return_exceptions=True)
        for result in worker_results:
            if isinstance(result, BaseException):
                if not fail_exc:
                    fail_exc.append(result)
        if fail_exc:
            raise fail_exc[0]


async def codegen_task(
        plan: ReportPlanOutput | dict,
        task: PlanTask | dict,
        *,
        rid: str,
        tools: list[str] | None = None,
        fix_error: str | None = None,
        instruction_extra: str | None = None,
        user_description: str | None = None,
        report_query: str | None = None,
        retry_sink: list[dict[str, Any]] | None = None,
) -> TaskOutput:
    """LLM-codegen a single plan task and validate before saving ``srcs/{task_id}.py``.

    Args:
        plan: Report plan (model or dict).
        task: Target task definition.
        rid: Report id under ``reports/{rid}/``.
        tools: MCP tool paths available to this task.
        fix_error: Prior execution/validation error for retry feedback.
        instruction_extra: User override appended to task instruction.
        user_description: Report-level user description for attach context.
        report_query: Original report query for attach context.
        retry_sink: Optional callback list for retry telemetry.

    Returns:
        Validated :class:`TaskOutput` with generated ``code``.

    흐름:
      plan.instruction (+ 사용자 수정 / 이전 오류 lesson)
        → TaskCodegenNode.run (_lesson_flush=False: 태스크 성공 후 runner 가 flush)
        → task_shell (body 추출 → validate → prelude 조립)
        → validate_codegen_output (타입별·MCP·board validator)
        → validate_task_code (syntax + 공통 anti-pattern)
        → save_task_source
    """
    plan_d = _plan_dict(plan)
    task_d = _task_dict(task)
    instruction = task_d["instruction"]
    # type → nodes/report/task/{type} NodeV 인스턴스
    node = get_task_node(task_d["type"])
    if instruction_extra:
        # report/update 의 query 를 태스크 미션에 덧붙임
        instruction = (
            f"{instruction}\n\n"
            "## 사용자 수정 요청\n"
            f"{instruction_extra.strip()}\n"
        )
    if fix_error:
        # MAX_TASK_SOURCE_RETRIES 재시도: traceback 을 압축·힌트화해 instruction 주입
        from sage.nodes.lesson_learn import (
            compress_error_for_lesson,
            format_retry_feedback,
            format_validator_system_priority_block,
            infer_lesson_category,
            lessons_prompt_block,
        )
        from sage.report.exec_hints import execution_fix_hints

        category = infer_lesson_category(fix_error)
        core = compress_error_for_lesson(fix_error)
        hints = execution_fix_hints(fix_error)
        block = core or fix_error.strip()[:800]
        if hints:
            block = f"{block}\n\n## 수정 힌트\n{hints}"
        lessons_block = ""
        # validated.md 누적 lesson — 같은 유형 실패를 반복하지 않도록
        if node.validated and node.validated.exists():
            lessons_block = lessons_prompt_block(
                node.validated.read_text(encoding="utf-8")
            )
        priority = format_validator_system_priority_block(
            category, core or fix_error, attempt=1
        )
        instruction = (
            f"{priority}"
            f"{instruction}\n\n"
            f"{format_retry_feedback(category, core or fix_error, attempt=1)}\n"
            f"{lessons_block}"
            "## 이전 생성 소스 오류 — 수정 후 재생성\n"
            f"```\n{block}\n```"
        )

    def _on_retry(**payload: Any) -> None:
        # NodeV 내부 재시도 텔레메트리 → _iter_one_plan_task 가 SSE retrying 으로 변환
        if retry_sink is not None:
            retry_sink.append(payload)

    out: TaskOutput = await node.run(
        plan_id=plan_d["plan_id"],
        data_id=plan_d["data_id"],
        task_id=task_d["task_id"],
        type=task_d["type"],
        title=task_d["title"],
        description=task_d.get("description") or "",
        instruction=instruction,
        context=list(task_d.get("context") or []),
        rid=rid,
        tools=list(tools or []),
        plan_task_ids=[t["task_id"] for t in plan_d.get("tasks") or []],
        user_description=user_description,
        report_query=report_query,
        _retry_sink=_on_retry,
        # runner 가 execute 성공/실패 시점에 flush — NodeV 중간 flush 방지
        _lesson_flush=False,
    )
    from sage.report.task_shell import assemble_task_source, extract_task_body
    from sage.report.validators import validate_codegen_output
    from sage.logg import debug

    try:
        await validate_codegen_output(
            out.code,
            task_type=task_d["type"],
            plan_id=plan_d["plan_id"],
            data_id=plan_d["data_id"],
            rid=rid,
            context=list(task_d.get("context") or []),
            tools=list(tools or []),
        )
    except ValueError as exc:
        from sage.nodes.lesson_learn import infer_lesson_category

        node.note_failure(
            infer_lesson_category(str(exc)),
            str(exc),
            phase="post_validate",
        )
        await node.record_immediate_lesson_async(infer_lesson_category(str(exc)), str(exc), phase="post_validate")
        raise TaskSourceError(str(exc)) from exc

    try:
        body = extract_task_body(out.code)
    except ValueError as exc:
        from sage.nodes.lesson_learn import infer_lesson_category

        node.note_failure(infer_lesson_category(str(exc)), str(exc), phase="post_validate")
        await node.record_immediate_lesson_async(infer_lesson_category(str(exc)), str(exc), phase="post_validate")
        raise TaskSourceError(str(exc)) from exc

    assembled = assemble_task_source(body)
    if assembled != out.code:
        debug(f"[codegen] {task_d['task_id']} assembled task shell")
    out = out.model_copy(update={"code": assembled})

    try:
        validate_task_code(out.code, task_d["task_id"])
    except TaskSourceError as exc:
        from sage.nodes.lesson_learn import infer_lesson_category

        node.note_failure(
            infer_lesson_category(str(exc)),
            str(exc),
            phase="post_validate",
        )
        await node.record_immediate_lesson_async(infer_lesson_category(str(exc)), str(exc), phase="post_validate")
        raise
    save_task_source(rid, task_d["task_id"], out.code)
    return out


async def run_task_code(
        source_path: Path,
        run: TaskRun,
        ctx: TaskContext,
        reporter: TaskReporter | None = None,
) -> None:
    """Import and run ``run_task`` from a saved task source file.

    ``SAGE_EXEC_DRIVER=docker_pool`` — warm pool worker 에 dispatch. pool 실패 시 fail-fast.
    """
    if not source_path.is_file():
        raise TaskSourceError(f"태스크 소스 없음: {source_path}")

    rid = ctx.rid or ""
    from sage.exec.jobs import build_report_task_job
    from sage.exec.runtime import run_exec_job

    job = build_report_task_job(
        source_path=source_path,
        run=run,
        ctx=ctx,
        rid=rid,
    )
    result = await run_exec_job(job, reporter=reporter)

    if not result.ok:
        err = result.error or "태스크 실행 실패"
        if result.exit_code in (124, 125) or is_exec_platform_error(err):
            raise ExecPlatformError(err)
        raise TaskSourceError(err)

    fresh = TaskContext.load(run.plan_id, rid=ctx.rid)
    ctx.tasks = fresh.tasks


async def run_task(
        plan: ReportPlanOutput | dict,
        task: PlanTask | dict,
        ctx: TaskContext,
        *,
        rid: str,
        reporter: TaskReporter | None = None,
        ctx_lock: asyncio.Lock | None = None,
) -> None:
    """저장된 srcs/{task_id}.py 실행 후 TaskContext 를 디스크에 저장.

    ctx_lock: 병렬 DAG 에서 여러 태스크가 동시에 ctx.save() 하지 않도록.
    칠판 쓰기는 태스크 내부 update_task 시점에 일어나며, save 는 스냅샷 플러시.
    """
    plan_d = _plan_dict(plan)
    task_d = _task_dict(task)
    run = TaskRun.from_plan(plan_d, task_d)
    await run_task_code(task_source_path(rid, run.task_id), run, ctx, reporter=reporter)
    if ctx_lock is not None:
        async with ctx_lock:
            ctx.save()
    else:
        ctx.save()


async def _iter_one_plan_task(
        plan: ReportPlanOutput,
        task: PlanTask,
        ctx: TaskContext,
        *,
        rid: str,
        tools: list[str] | None = None,
        index: int = 1,
        total: int = 1,
        instruction_extra: str | None = None,
        user_description: str | None = None,
        report_query: str | None = None,
        ctx_lock: asyncio.Lock | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """단일 태스크 lifecycle: codegen → exec → (실패 시 재생성) → executed SSE.

    바깥 루프: MAX_TASK_SOURCE_RETRIES
      - syntax/post_validate/execute source_error → fix_error=traceback 로 재 codegen
      - Quota / LLMTimeout / ContextAttachTooLarge → 즉시 raise (루프 중단)
      - connection_error → 즉시 failed (재생성 무의미)
    성공 시 break 후 catalog 를 result 로 yield (codegen 객체는 라우터가 DB persist).
    """
    plan_d = _plan_dict(plan)
    task_d = _task_dict(task)
    # 태스크별 MCP path — data 타입은 plan.tools 상속, 그 외는 명시/metadata
    task_tools = resolve_task_tool_paths(
        plan_d.get("tools"),
        task_d.get("tools"),
        task_type=task_d["type"],
        data_id=plan_d.get("data_id"),
    )
    out: TaskOutput | None = None
    last_err: str | None = None
    # NodeV._retry_sink 가 append → 폴링 루프가 SSE retrying 으로 변환
    codegen_retries: list[dict[str, Any]] = []
    task_node = get_task_node(task_d["type"])

    for attempt in range(1, MAX_TASK_SOURCE_RETRIES + 1):
        codegen_retries.clear()
        if attempt > 1:
            yield {
                "event": "retrying",
                "msg": (
                    f"[{task.title}] 소스 재생성 ({attempt}/{MAX_TASK_SOURCE_RETRIES})…"
                ),
                "task_id": task.task_id,
                "task_type": task.type,
                "rid": rid,
                "phase": "execute",
                "error": last_err,
            }

        yield {
            "event": "generating",
            "msg": (
                    f"({index}/{total}) [{task.title}] 작업 소스 생성 중…"
                    + (f" (재시도 {attempt})" if attempt > 1 else "")
            ),
            "task_id": task.task_id,
            "task_type": task.type,
            "rid": rid,
        }
        try:
            # codegen 을 task 로 띄운 뒤 sink 를 폴링 — LLM 장시간 대기 중에도
            # NodeV 내부 재시도를 SSE 로 실시간 전달
            codegen_job = asyncio.create_task(
                codegen_task(
                    plan, task, rid=rid, tools=task_tools,
                    fix_error=last_err if attempt > 1 else None,
                    instruction_extra=instruction_extra,
                    user_description=user_description,
                    report_query=report_query,
                    retry_sink=codegen_retries,
                )
            )
            while not codegen_job.done():
                while codegen_retries:
                    ev = codegen_retries.pop(0)
                    err = ev.get("error", "")
                    kind = ev.get("kind", "")
                    yield {
                        "event": "retrying",
                        "msg": (
                            f"[{task.title}] codegen 재시도 "
                            f"({ev.get('attempt')}/{ev.get('max_attempts')}) "
                            f"[{ev.get('kind')}]"
                        ),
                        "task_id": task.task_id,
                        "task_type": task.type,
                        "rid": rid,
                        "phase": "codegen",
                        "error": err,
                    }
                await asyncio.sleep(0.05)
            out = await codegen_job
            # job 완료 직후 남은 sink 이벤트 flush
            while codegen_retries:
                ev = codegen_retries.pop(0)
                kind = ev.get("kind", "")
                err = ev.get("error", "")
                yield {
                    "event": "retrying",
                    "msg": (
                        f"[{task.title}] codegen 재시도 "
                        f"({ev.get('attempt')}/{ev.get('max_attempts')}) "
                        f"[{ev.get('kind')}]"
                    ),
                    "task_id": task.task_id,
                    "task_type": task.type,
                    "rid": rid,
                    "phase": "codegen",
                    "error": ev.get("error", ""),
                }
        except CodegenContractError as exc:
            last_err = str(exc)
            yield {
                "event": "retrying" if attempt < MAX_TASK_SOURCE_RETRIES else "failed",
                "msg": (
                    f"[{task.title}] contract 위반 — 같은 요청에서 소스 재생성 "
                    f"({attempt}/{MAX_TASK_SOURCE_RETRIES})"
                ),
                "task_id": task.task_id,
                "task_type": task.type,
                "rid": rid,
                "phase": "codegen",
                "error": last_err,
            }
            if attempt >= MAX_TASK_SOURCE_RETRIES:
                await task_node.flush_learned_lessons_async(resolved=False)
                raise TaskSourceError(last_err) from exc
            continue
        except TaskSourceError as exc:
            last_err = str(exc)
            if is_exec_platform_error(last_err):
                yield {
                    "event": "failed",
                    "msg": f"[{task.title}] exec 플랫폼 오류 — 재생성 없음: {exc}",
                    "task_id": task.task_id,
                    "task_type": task.type,
                    "rid": rid,
                    "phase": "execute",
                    "error": last_err,
                }
                await task_node.flush_learned_lessons_async(resolved=False)
                raise ExecPlatformError(last_err) from exc
            # post_validate / syntax — 다음 attempt 의 fix_error 로 전달
            yield {
                "event": "retrying" if attempt < MAX_TASK_SOURCE_RETRIES else "failed",
                "msg": f"[{task.title}] 소스 문법 오류: {exc}",
                "task_id": task.task_id,
                "task_type": task.type,
                "rid": rid,
                "phase": "syntax",
                "error": last_err,
            }
            if attempt >= MAX_TASK_SOURCE_RETRIES:
                await task_node.flush_learned_lessons_async(resolved=False)
                raise
            continue
        # 인프라·한도성 오류는 재생성해도 해결 안 됨 → 그대로 전파
        except QuotaExceededError:
            raise
        except LLMTimeoutError:
            raise
        except ContextAttachTooLargeError:
            raise
        except MaxRetriesExceededError as exc:
            if is_quota_error(exc.last_error):
                raise QuotaExceededError() from exc
            last_err = exc.last_error or str(exc)
            yield {
                "event": "retrying" if attempt < MAX_TASK_SOURCE_RETRIES else "failed",
                "msg": f"[{task.title}] codegen {exc.message}",
                "task_id": task.task_id,
                "task_type": task.type,
                "rid": rid,
                "phase": "codegen",
                "error": last_err,
            }
            if attempt >= MAX_TASK_SOURCE_RETRIES:
                await task_node.flush_learned_lessons_async(resolved=False)
                raise
            continue
        except Exception as exc:
            err_msg = traceback.format_exc()
            yield {
                "event": "failed",
                "msg": f"[{task.title}] codegen 실패: {exc}",
                "task_id": task.task_id,
                "task_type": task.type,
                "rid": rid,
                "phase": "codegen",
                "error": err_msg,
            }
            raise

        src_path = task_source_path(rid, task.task_id)
        yield {
            "event": "generated",
            "msg": f"[{task.title}] 소스 생성 완료 → {src_path.name} ({len(out.code):,} bytes)",
            "task_id": task.task_id,
            "task_type": task.type,
            "rid": rid,
            "description": out.description,
        }

        yield {
            "event": "executing",
            "msg": f"[{task.title}] {TASK_TYPE_INTRO.get(task.type, '실행 중…')}",
            "task_id": task.task_id,
            "task_type": task.type,
            "rid": rid,
        }
        # --- 실행 단계: reporter drain → progress SSE ---
        reporter = TaskReporter()
        reporter.update(
            f"▶ [{task.title}] {TASK_TYPE_INTRO.get(task.type, '실행')}",
            state="running",
        )
        try:
            exec_task = asyncio.create_task(
                run_task(plan, task, ctx, rid=rid, reporter=reporter, ctx_lock=ctx_lock)
            )
            # safe_report/reporter.update 가 sync 로 쌓은 메시지를 주기적으로 SSE 화
            while not exec_task.done():
                for msg in reporter.drain():
                    yield {
                        "event": "progress",
                        "msg": msg,
                        "task_id": task.task_id,
                        "task_type": task.type,
                        "rid": rid,
                    }
                await asyncio.sleep(0.05)
            await exec_task
            for msg in reporter.drain():
                yield {
                    "event": "progress",
                    "msg": msg,
                    "task_id": task.task_id,
                    "task_type": task.type,
                    "rid": rid,
                }
            reporter.update(f"✓ [{task.title}] 완료", state="completed")
            # 축적된 failure lesson 을 validated.md 에 성공(resolved)으로 기록
            try:
                await task_node.flush_learned_lessons_async(resolved=True)
            except Exception as exc:
                warning(f"[{task.title}] validated.md flush skipped: {exc}")
            break
        except ExecPlatformError as exc:
            err_msg = str(exc)
            yield {
                "event": "failed",
                "msg": f"[{task.title}] exec 플랫폼 오류 — 재생성 없음: {exc}",
                "task_id": task.task_id,
                "task_type": task.type,
                "rid": rid,
                "phase": "execute",
                "error": err_msg,
            }
            await task_node.flush_learned_lessons_async(resolved=False)
            raise
        except Exception as exc:
            err_msg = traceback.format_exc()
            if isinstance(exc, TaskSourceError) and is_exec_platform_error(err_msg):
                yield {
                    "event": "failed",
                    "msg": f"[{task.title}] exec 플랫폼 오류 — 재생성 없음: {exc}",
                    "task_id": task.task_id,
                    "task_type": task.type,
                    "rid": rid,
                    "phase": "execute",
                    "error": err_msg,
                }
                await task_node.flush_learned_lessons_async(resolved=False)
                raise ExecPlatformError(err_msg) from exc
            if is_connection_error(exc):
                # MCP 다운 등 — 소스를 고쳐도 소용없으므로 fail-fast
                yield {
                    "event": "failed",
                    "msg": f"[{task.title}] 연결 오류 — 재시도 없음: {exc}",
                    "task_id": task.task_id,
                    "task_type": task.type,
                    "rid": rid,
                    "error": err_msg,
                }
                raise
            if is_source_error(exc) and attempt < MAX_TASK_SOURCE_RETRIES:
                # 실행 traceback 전체를 fix_error 로 다음 codegen 에 전달
                last_err = err_msg
                from sage.nodes.lesson_learn import infer_lesson_category

                cat = infer_lesson_category(err_msg)
                task_node.note_failure(
                    cat,
                    err_msg,
                    phase="execute",
                    attempt=attempt,
                )
                await task_node.record_immediate_lesson_async(cat, err_msg, phase="execute")
                yield {
                    "event": "retrying",
                    "msg": (
                        f"[{task.title}] 소스 실행 오류 — traceback 전달 후 재생성 "
                        f"({attempt + 1}/{MAX_TASK_SOURCE_RETRIES})"
                    ),
                    "task_id": task.task_id,
                    "task_type": task.type,
                    "rid": rid,
                    "phase": "execute",
                    "error": err_msg,
                }
                continue
            yield {
                "event": "failed",
                "msg": f"[{task.title}] 실행 실패: {exc}",
                "task_id": task.task_id,
                "task_type": task.type,
                "rid": rid,
                "phase": "execute",
                "error": err_msg,
            }
            await task_node.flush_learned_lessons_async(resolved=False)
            raise

    assert out is not None

    # payload 없는 catalog (key 목록) — SSE 대역폭 절약 + 라우터 DB persist 용
    board = ctx.catalog([task.task_id])
    key_names = ", ".join(board.get(task.task_id, {}).get("keys", {}).keys()) or "(없음)"
    msg = f"[{task.title}] 실행 완료 — 산출 key: {key_names}"
    executed: dict[str, Any] = {
        "event": "executed",
        "msg": msg,
        "task_id": task.task_id,
        "task_type": task.type,
        "rid": rid,
        "result": board,
        # 라우터만 사용 — _sse 가 클라이언트 전송 전 pop
        "codegen": out,
    }
    yield executed


async def iter_plan_tasks(
        plan: ReportPlanOutput,
        ctx: TaskContext,
        *,
        rid: str,
        tools: list[str] | None = None,
        only_tasks: set[str] | None = None,
        instruction_extra: str | None = None,
        user_description: str | None = None,
        report_query: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Generate and execute plan tasks in topological order (parallel when independent).

    Args:
        plan: Validated report plan DAG.
        ctx: Task result board persisted under the plan hex directory.
        rid: Report id for artifact paths.
        tools: MCP tool paths available during codegen.
        only_tasks: Subset of task ids to run (others skipped).
        instruction_extra: User override appended during codegen.
        user_description: Report description for LLM attach.
        report_query: Original user query for LLM attach.

    Yields:
        SSE-style dicts: ``generating``, ``executing``, ``executed``, ``failed``, etc.
    """
    ordered = topo_sort_tasks(plan.tasks)
    index_map = {t.task_id: i + 1 for i, t in enumerate(ordered)}
    total = len(ordered)
    ctx_lock = asyncio.Lock()

    async def task_runner(task: PlanTask):
        async for ev in _iter_one_plan_task(
                plan,
                task,
                ctx,
                rid=rid,
                tools=tools,
                index=index_map[task.task_id],
                total=total,
                instruction_extra=instruction_extra,
                user_description=user_description,
                report_query=report_query,
                ctx_lock=ctx_lock,
        ):
            yield ev

    async for ev in _iter_tasks_parallel(
            plan,
            rid=rid,
            task_runner=task_runner,
            only_tasks=only_tasks,
    ):
        yield ev


async def _iter_one_report_exec_task(
        plan: ReportPlanOutput,
        task: PlanTask,
        ctx: TaskContext,
        *,
        rid: str,
        run_dir: Path,
        index: int = 1,
        total: int = 1,
        ctx_lock: asyncio.Lock | None = None,
) -> AsyncIterator[dict[str, Any]]:
    logs_dir = run_dir / "logs"
    log = RunTaskLog(logs_dir / f"{task.task_id}.log")
    log.append(f"=== {task.task_id} ({task.type}) ===")

    src = task_source_path(rid, task.task_id)
    if not src.is_file():
        msg = f"태스크 소스 없음: {src}"
        log.append(f"[failed] {msg}")
        yield {
            "event": "failed",
            "msg": f"[{task.title}] {msg}",
            "task_id": task.task_id,
            "task_type": task.type,
            "rid": rid,
            "phase": "execute",
            "error": msg,
        }
        raise TaskSourceError(msg)

    yield {
        "event": "executing",
        "msg": f"({index}/{total}) [{task.title}] {TASK_TYPE_INTRO.get(task.type, '실행 중…')}",
        "task_id": task.task_id,
        "task_type": task.type,
        "rid": rid,
    }

    reporter = RunTaskReporter(log)
    reporter.update(
        f"▶ [{task.title}] {TASK_TYPE_INTRO.get(task.type, '실행')}",
        state="running",
    )
    try:
        exec_task = asyncio.create_task(
            run_task(plan, task, ctx, rid=rid, reporter=reporter, ctx_lock=ctx_lock)
        )
        while not exec_task.done():
            for msg in reporter.drain():
                log.append(msg)
                yield {
                    "event": "progress",
                    "msg": msg,
                    "task_id": task.task_id,
                    "task_type": task.type,
                    "rid": rid,
                }
            await asyncio.sleep(0.05)
        await exec_task
        for msg in reporter.drain():
            log.append(msg)
            yield {
                "event": "progress",
                "msg": msg,
                "task_id": task.task_id,
                "task_type": task.type,
                "rid": rid,
            }
        reporter.update(f"✓ [{task.title}] 완료", state="completed")
    except Exception as exc:
        err_msg = traceback.format_exc()
        log.append(f"[failed]\n{err_msg}")
        yield {
            "event": "failed",
            "msg": f"[{task.title}] 실행 실패: {exc}",
            "task_id": task.task_id,
            "task_type": task.type,
            "rid": rid,
            "phase": "execute",
            "error": err_msg,
        }
        raise

    board = ctx.catalog([task.task_id])
    yield {
        "event": "executed",
        "msg": (
            f"[{task.title}] 실행 완료 — 산출 key: "
            f"{', '.join(board.get(task.task_id, {}).get('keys', {}).keys()) or '(없음)'}"
        ),
        "task_id": task.task_id,
        "task_type": task.type,
        "rid": rid,
        "result": board,
    }
    await asyncio.sleep(0.05)


async def iter_report_exec(
        plan: ReportPlanOutput,
        ctx: TaskContext,
        *,
        rid: str,
        run_dir: Path,
        only_tasks: set[str] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Execute saved task sources without codegen (published report runs).

    Args:
        plan: Report plan DAG.
        ctx: Task result board (loaded or fresh for the run).
        rid: Report id whose ``srcs/*.py`` files are executed.
        run_dir: Run artifact directory under ``cfg.runs_path``.
        only_tasks: Optional subset of task ids to execute.

    Yields:
        SSE-style dicts: ``executing``, ``progress``, ``executed``, ``failed``, etc.
    """
    ordered = topo_sort_tasks(plan.tasks)
    index_map = {t.task_id: i + 1 for i, t in enumerate(ordered)}
    total = len(ordered)
    ctx_lock = asyncio.Lock()

    async def task_runner(task: PlanTask):
        async for ev in _iter_one_report_exec_task(
                plan,
                task,
                ctx,
                rid=rid,
                run_dir=run_dir,
                index=index_map[task.task_id],
                total=total,
                ctx_lock=ctx_lock,
        ):
            yield ev

    async for ev in _iter_tasks_parallel(
            plan,
            rid=rid,
            task_runner=task_runner,
            only_tasks=only_tasks,
    ):
        yield ev


def collect_report_result(
        plan: ReportPlanOutput,
        ctx: TaskContext,
        rid: str,
        *,
        generation_started_at: datetime | str | None = None,
        generation_duration_sec: float | None = None,
        llm_usage: dict[str, Any] | None = None,
        artifact_dir: Path | None = None,
) -> dict[str, Any]:
    """generate/update 완료 시 최종 artifact 수집.

    1. release 태스크의 report|layout|report_layout 키 → finalize_report_document
    2. narrative 의 report_document → draft.json (초안)
    3. quality lint + generation meta (시간·LLM usage)
    4. TaskContext 전체 스냅샷 → context.json
    artifact_dir 가 있으면 reports/{rid} 대신 그 경로에 기록 (테스트/실험용).
    """
    from sage.report.layout import finalize_report_document, simplify_report_tasks
    from sage.report.meta import attach_generation_meta, build_pipeline_meta
    from sage.report.context_keys import (
        NARRATIVE_DRAFT_KEY,
        RELEASE_REPORT_KEYS,
        RELEASE_SUMMARY_KEY,
    )

    out_dir = artifact_dir or report_dir(rid)

    def _save(name: str, payload: Any) -> Path:
        return save_json_artifact(out_dir / f"{name}.json", payload)

    generation_meta = build_pipeline_meta(
        started_at=generation_started_at,
        duration_sec=generation_duration_sec,
        llm_usage=llm_usage,
    )
    if llm_usage:
        if artifact_dir is None:
            save_json_artifact(out_dir / "usage.json", generation_meta)
        else:
            _save("usage", generation_meta)

    task_board = ctx.catalog()
    report = None
    draft = None
    release_summary = None
    # 키 이름 — context_keys (legacy layout/report_layout 호환)
    for task in plan.tasks:
        if task.type == "release":
            report = None
            for rk in RELEASE_REPORT_KEYS:
                report = ctx.get_result(task.task_id, rk)
                if report is not None:
                    break
            release_summary = ctx.get_result(task.task_id, RELEASE_SUMMARY_KEY)
        elif task.type == "narrative":
            draft = ctx.get_result(task.task_id, NARRATIVE_DRAFT_KEY)

    if report is not None:
        # catalog visual attach, legacy block 정규화, meta sanitize
        report = finalize_report_document(
            report,
            task_catalog=task_board,
            plan_id=plan.plan_id,
            did=plan.data_id,
            rid=rid,
            title=plan.title,
            description=plan.description,
        )
        from sage.report.quality import lint_report_document

        report["quality"] = lint_report_document(report)
        if release_summary is not None:
            report["release_summary"] = release_summary
        report = attach_generation_meta(
            report,
            started_at=generation_started_at,
            duration_sec=generation_duration_sec,
            llm_usage=llm_usage,
        )
        if artifact_dir is None:
            save_report_artifact(rid, "report", report)
        else:
            _save("report", report)
    if draft is not None:
        if artifact_dir is None:
            save_report_artifact(rid, "draft", draft)
        else:
            _save("draft", draft)

    if ctx is not None:
        if artifact_dir is None:
            save_report_artifact(rid, "context", ctx.to_dict())
        else:
            _save("context", ctx.to_dict())

    return {
        "rid": rid,
        "report_dir": str(report_dir(rid)),
        "artifact_dir": str(out_dir),
        "report": report,
        "draft": draft,
        "generation": generation_meta,
        # UI용 요약 칠판 (payload 제외)
        "tasks": simplify_report_tasks(task_board) if task_board else {},
        "context_file": ctx.context_file,
    }
