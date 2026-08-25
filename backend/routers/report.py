"""Report HTTP API — plan, codegen, execute, publish, and update (SSE)."""

import asyncio
import json
import shutil
import time
import traceback
from typing import List
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette import EventSourceResponse
from pydantic import ValidationError

import cfg
from sage import nodes
from sage.db import SAGEDataStore, saged, get_db
from sage.llm import (
    begin_report_generation,
    current_usage,
    format_usage_brief,
    persist_report_usage_log,
    reset_report_generation,
)
from sage.errs import MaxRetriesExceededError, QuotaExceededError, LLMTimeoutError, ContextAttachTooLargeError
from sage.logg import error, warning, debug, LoggingRoute, close_report_log, log_console_brief, log_report_log_link, \
    open_report_log
from routers.base import APIResponse, SSEEncoder, DeleteResponse
from sage.models import doc

from sage.models.node import ReportPlanOutput, TaskOutput
from sage.models.req import ReportGenerateRequest, ReportExecRequest, ReportListRequest, ReportUpdateRequest, ReportAssetizeRequest, \
    ReportDeleteRequest, ReportPublishRequest
from sage.report.plan_tools import finalize_plan_tools, resolve_task_tool_paths
from sage.config import TOOLS_DIR
from sage.report.runner import (
    collect_report_result,
    downstream_task_closure,
    ensure_report_dirs,
    iter_plan_tasks,
    iter_report_exec,
    load_plan_from_report,
    make_run_dir,
    missing_task_sources,
    report_dir,
    save_plan,
    save_run_meta,
    task_context_for_report,
)

router = APIRouter(
    prefix="/report",  # 공통 경로 접두어
    tags=["report"],  # Swagger 문서상의 그룹 이름
    route_class=LoggingRoute
)


@router.post("/list/query", response_model=APIResponse[List[doc.Report]])
async def list_reports(
    req: ReportListRequest, 
    saged: SAGEDataStore = Depends(get_db)
):
    """
    리포트 목록 조회 (JSON Body 요청)
    - status가 없거나 빈 배열이면 전체 리포트 조회
    - status에 ["completed", "published"] 등 배열을 전달하면 해당 상태들을 OR 조건으로 필터링
    """
    try:
        col = saged.get_collection(doc.Report)
        
        # 1. status 배열 유무에 따른 MongoDB $in 쿼리 구성
        query = {}
        if req.status:
            query = {"status": {"$in": req.status}}

        # 2. DB 조회 및 모델 검증
        cursor = col.find(query)
        report_list = []
        
        async for cur in cursor:
            try:
                report_list.append(doc.Report.model_validate(cur))
            except ValidationError:
                # 스키마 구조가 깨진 데이터는 스킵하여 API 안정성 확보
                continue

        return APIResponse[List[doc.Report]](success=True, result=report_list)

    except Exception as e:
        return APIResponse[List[doc.Report]](
            success=False,
            error=f"리포트 목록을 불러오는 중 오류가 발생했습니다: {str(e)}",
        )

        
@router.post("/generate")
async def generate_report(req: ReportGenerateRequest):
    """Start full report generation; streams SSE via :func:`handle_report_generation`."""
    return EventSourceResponse(
        handle_report_generation(req, saged)
    )


@router.patch("/update")
async def update_report(req: ReportUpdateRequest):
    """
    보고서 플랜 중 특정 단계 재생성 (SSE)
    """
    return EventSourceResponse(
        handle_report_update(req, saged)  # saged는 외부에서 주입된 DB 객체로 가정
    )


@router.post("/publish", response_model=APIResponse[doc.Report])
async def publish_report(
    req: ReportPublishRequest,
    db: SAGEDataStore = Depends(get_db),
):
    """
    보고서를 published 상태로 변경하여 실행(exec) 가능하게 합니다.
    """
    try:
        report_doc = await db.load(doc.Report, req.rid)
        if not report_doc:
            return APIResponse[doc.Report](
                success=False,
                error=f"보고서를 찾을 수 없습니다: {req.rid}",
            )

        report_doc.status = "published"
        report_doc.updated_at = datetime.now(timezone.utc)
        await db.save(report_doc)

        return APIResponse[doc.Report](success=True, result=report_doc)

    except Exception as e:
        return APIResponse[doc.Report](
            success=False,
            error=f"보고서 발행 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/exec")
async def exec_report(req: ReportExecRequest):
    """
    published 상태의 보고서 rid를 바탕으로 실제 데이터를 생성(Execution)합니다.
    """
    return EventSourceResponse(
        handle_report_execution(req.rid, saged)
    )


@router.delete("/delete", response_model=DeleteResponse)
async def delete_reports(
        req: ReportDeleteRequest,
        saged: SAGEDataStore = Depends(get_db)
):
    """
    리포트 일괄 삭제 API
    - all: 전체 리포트 및 연관 데이터(Plan, Task, Execution) 삭제
    - exclude: 특정 rid 배열을 제외한 모든 리포트 및 연관 데이터 삭제
    - list: 주어진 rid 배열에 해당하는 리포트 및 연관 데이터 삭제
    """
    # ------------------------------------------------------------------
    # 삭제 모드 설계 의도
    # - FE/운영에서 "전부 비우기 / 몇 개만 남기기 / 골라 지우기" 를 한 API 로 처리.
    # - 타겟 rid 목록을 먼저 확정한 뒤, rid 단위로 Plan/Task/Execution + 본체 + 디스크를
    #   지우면 부분 실패 시에도 어느 rid 가 남았는지 추적 가능.
    # ------------------------------------------------------------------

    # 1. 모드별 타겟 rid 목록 추출
    target_rids = []

    try:
        if req.mode == "all":
            # "rp-" 접두사로 reports 컬렉션 전체를 조회.
            # 본문 없이 _id 만 받는 list_all_ids 를 쓰는 이유: 대량 삭제 시 페이로드 최소화.
            target_rids = await saged.list_all_ids("rp-")

        elif req.mode == "exclude":
            # exclude = (전체 − 보존 목록). ids 없으면 "보존할 대상 없음"이 아니라
            # 요청이 모호해지므로 400 — all 모드를 쓰라고 유도.
            if not req.ids:
                raise HTTPException(status_code=400, detail="exclude 모드에서는 제외할 rids 배열이 필수입니다.")

            all_rids = await saged.list_all_ids("rp-")
            # set 으로 O(1) 멤버십 — id 수가 많아져도 전체 스캔은 1회만.
            exclude_set = set(req.ids)
            target_rids = [rid for rid in all_rids if rid not in exclude_set]

        elif req.mode == "list":
            # 명시 목록만 삭제. DB 조회 없이 클라이언트가 준 id 를 그대로 타겟으로 씀
            # (이미 없은 rid 는 루프에서 실패/빈 삭제로 흡수).
            if not req.ids:
                raise HTTPException(status_code=400, detail="list 모드에서는 삭제할 rids 배열이 필수입니다.")
            target_rids = req.ids

        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 mode 값입니다. ('all', 'exclude', 'list' 중 선택)")

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 대상 식별 중 오류: {str(e)}")

    if not target_rids:
        # 빈 타겟은 에러가 아니라 성공 — idempotent 삭제 UX (이미 비어 있음).
        return DeleteResponse(
            status="success",
            id=str(req.ids or []),
            message="삭제할 대상 리포트가 없습니다."
        )

    # 2. 루프를 돌며 DB 메타데이터 및 연관 데이터 삭제 진행
    # 한 rid 실패가 전체를 멈추지 않게 개별 try — 운영 배치에서 "나머지라도 지움".
    success_rids = []
    failed_rids = []

    for rid in target_rids:
        try:
            # Report 단독 삭제 시 orphan Plan/Task/Execution 이 남으므로
            # 외래키처럼 rid 로 묶인 자식을 먼저 비움.
            await saged.delete_many(doc.Plan, {"rid": rid})
            await saged.delete_many(doc.Task, {"rid": rid})
            await saged.delete_many(doc.Execution, {"rid": rid})

            # 리포트 본체 — 데이터셋(did-) 과 동일하게 문자열 _id(rid) 로 직접 delete.
            await saged.delete(rid)

            # 디스크 산출물(srcs, draft, report.json 등)도 함께 제거해야
            # 동일 rid 재생성/재사용 시 이전 아티팩트가 섞이지 않음.
            target_dir = cfg.root_path / Path(f"reports/{rid}")

            if target_dir.exists() and target_dir.is_dir():
                # path traversal 방어: 반드시 cfg.root_path 하위여야 rmtree.
                if cfg.root_path in target_dir.parents:
                    shutil.rmtree(target_dir)

            success_rids.append(rid)

        except Exception as e:
            print(f"rid {rid} 및 연관 데이터 삭제 중 에러 발생")
            print(traceback.format_exc())
            failed_rids.append({"rid": rid, "reason": str(e)})

    # 3. 부분 성공을 partial_success 로 구분 — FE 가 재시도 대상을 고를 수 있게.
    status_str = "partial_success" if failed_rids else "success"

    return DeleteResponse(
        status=status_str,
        id=str(req.ids or []),
        message=f"요청된 대상 중 {len(success_rids)}개의 리포트 및 관련 연관 데이터가 삭제되었습니다."
    )


@router.post("/assetize", deprecated=True)
async def assetize_report(req: ReportAssetizeRequest,
                          db: SAGEDataStore = Depends(get_db)):
    """
    이 API는 더 이상 사용이 의미없습니다. 보고서는 기존처럼 MCP 도구들로 구성되지 않고 순수 파이썬 소스로만 구성되서 보고서는 자산화(assetized)
    """
    try:
        # 1. 보고서 존재 확인
        report_doc = await db.load(doc.Report, req.rid)
        if not report_doc:
            raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

        # 2. 해당 보고서(rid)에 연결된 모든 Task 조회
        cursor = db.tasks.find({"rid": req.rid})
        tasks = await cursor.to_list(length=100)

        if not tasks:
            raise HTTPException(status_code=400, detail="자산화할 작업 결과가 없습니다.")

        promoted_tools = []

        # 3. 각 Task의 tool_id 폴더 확인 (tools 단일 루트)
        for task in tasks:
            tool_id = task.get("tool_id")
            if not tool_id:
                continue

            tool_dir = Path(TOOLS_DIR) / tool_id

            if tool_dir.exists() and tool_dir.is_dir():
                debug(f"Tool folder verified: {tool_dir}")

                # Tool DB 상태 업데이트
                # await db.tools.update_one(
                #     {"_id": tool_id},
                #     {
                #         "$set": {
                #             "status": "asset",
                #             "promoted_at": datetime.now(timezone.utc),
                #             "updated_at": datetime.now(timezone.utc)
                #         }
                #     }
                # )
                promoted_tools.append(tool_id)
            else:
                debug(f"Tool folder not found: {tool_dir}")

        # 6. 보고서 상태를 'promoted'로 변경
        await db.reports.update_one(
            {"_id": req.rid},
            {
                "$set": {
                    "status": "assetized",
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        return {
            "status": "success",
            "rid": req.rid,
            "message": f"{len(promoted_tools)}개의 도구 패키지가 Assets로 전환되었습니다.",
            "promoted_tools": promoted_tools
        }

    except Exception as e:
        error(f"[PromoteError] {req.rid}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Promotion failed: {str(e)}")


async def create_initial_session(db: SAGEDataStore, req: ReportGenerateRequest) -> doc.Session:
    """Create or reuse a chat session for a report generation request.

    Args:
        db: Document store.
        req: Request; uses ``session_id`` when continuing an existing session.

    Returns:
        Loaded or newly created :class:`~sage.models.doc.Session`.
    """
    if req.session_id:
        session = await db.load(doc.Session, req.session_id)
        if not session: raise ValueError("Session not found")
        return session

    session = doc.Session(
        session_id=f"sess-{uuid.uuid4().hex[:8]}",
        title_query=req.query,
        # user_id=req.user_id
    )
    await db.save(session)
    return session


def _sse(payload: dict):
    """report SSE — codegen 원문은 클라이언트로 보내지 않음 (용량·보안)."""
    event = payload.pop("event")
    msg = payload.pop("msg")
    payload.pop("codegen", None)
    return SSEEncoder.encode(event, msg, **payload)


def _client_report_payload(report_result: dict) -> dict:
    """collect_report_result 중 클라이언트 SSE에 필요한 필드만 (서버 경로 제외)."""
    return {
        "report": report_result.get("report"),
        "draft": report_result.get("draft"),
        "tasks": report_result.get("tasks"),
        "generation": report_result.get("generation"),
    }


async def _persist_task_execution(
        db: SAGEDataStore,
        session,
        plan: ReportPlanOutput,
        task_id: str,
        out: TaskOutput,
        board: dict,
        rid: str,
        tools: list,
) -> None:
    """태스크 1회 실행 완료 시 Tool/Task/Execution 3종 문서를 Mongo에 기록."""
    # ------------------------------------------------------------------
    # Why Tool + Task + Execution 을 분리 저장하는가?
    # - Tool(tm-*): 생성된 파이썬 코드(소스)의 재활용·자산화 단위.
    #   보고서는 더 이상 MCP로 구성되지 않아도, 과거 assetize/목록 UI는
    #   "도구 패키지" 관점으로 소스를 조회하므로 Tool 문서에 code 를 둔다.
    # - Task: 플랜 내 단계 메타(어느 plan/rid/session, 어떤 context·tools).
    #   Tool 과 1:1로 tool_id 를 묶어 "이 단계가 어떤 코드를 쓰는지" 추적.
    # - Execution: 그 순간의 board(결과 스냅샷). 같은 Task 를 여러 번 돌리면
    #   Execution 만 쌓이고, Tool/Task 메타는 upsert 성격으로 갱신된다.
    # 세 문서를 한 곳에 합치지 않는 이유: 목록/삭제/자산화 API가 각각
    # tm-/task-/exec- 접두사로 컬렉션을 순회하기 때문.
    # ------------------------------------------------------------------
    # task_id → 가상 tool_id: 실제 MCP 서버 경로가 없어도 tm- 네임스페이스로
    # tools 컬렉션·디스크 관례와 맞춤 (과거 자산화 호환 네이밍).
    tool_id = f"tm-{task_id.replace('task-', '')[:24]}"
    task = next(t for t in plan.tasks if t.task_id == task_id)
    await db.save(doc.Tool(
        tool_id=tool_id,
        title=task.title,
        description=out.description or task.description,
        code=out.code,
    ))
    await db.save(doc.Task(
        task_id=task_id,
        plan_id=plan.plan_id,
        rid=rid,
        session_id=session.session_id,
        tool_id=tool_id,
        title=task.title,
        description=task.description,
        context=task.context,
        tools=tools,
    ))
    await db.save(doc.Execution(
        exec_id=f"exec-{uuid.uuid4().hex[:8]}",
        target_type="task",
        target_id=task_id,
        session_id=session.session_id,
        rid=rid,
        result=board,
    ))


async def _handle_executed_event(
        db: SAGEDataStore,
        session,
        plan: ReportPlanOutput,
        task_id: str,
        out: TaskOutput,
        board: dict,
        rid: str,
) -> None:
    task = next(t for t in plan.tasks if t.task_id == task_id)
    task_tools = resolve_task_tool_paths(
        plan.tools, task.tools, task_type=task.type, data_id=plan.data_id,
    )
    await _persist_task_execution(
        db, session, plan, task_id, out, board, rid, task_tools,
    )


async def handle_report_generation(req: ReportGenerateRequest, db: SAGEDataStore):
    """Full report pipeline: plan → parallel task codegen → collect artifacts.

    Args:
        req: Generation request (``did``, ``query``, optional ``tools`` / ``description``).
        db: Mongo store for Report, Plan, Task, Session persistence.

    Yields:
        SSE payloads (``initializing``, ``planned``, ``generating``, ``executed``,
        ``completed``, ``failed``) via :func:`_sse`.
    """
    # ==================================================================
    # 파이프라인 스테이지 개요 (각 yield 가 FE 진행 UI 와 1:1)
    # 1) initializing — rid 확정
    # 2) planning     — report/plan 노드로 태스크 DAG·툴 경로 설계
    # 3) planned      — Report/Plan persist + 디스크 plan 저장 후 UI 갱신
    # 4) generating/executed — iter_plan_tasks: codegen+실행, SSE는 즉시,
    #    Mongo Tool/Task/Execution 저장은 백그라운드로 (스트림 지연 방지)
    # 5) completed    — collect_report_result 로 draft/report 아티팩트 수집
    # 실패 시 status=failed 기록 + phase 태그로 FE 가 원인군 구분
    # ==================================================================
    rid = f"rp-{uuid.uuid4().hex[:8]}"
    report_doc = None
    report_log = open_report_log(rid)
    log_report_log_link(rid, report_log)
    # wall-clock(시작 시각)와 perf(소요 초)를 분리 — 메타/사용량 리포트용.
    generation_started_at = datetime.now(timezone.utc)
    generation_started_perf = time.perf_counter()
    # 토큰 usage ContextVar 시작 — finally 에서 reset (요청 간 누수 방지).
    begin_report_generation()

    try:
        # --- Stage: initializing ---
        # rid 를 먼저 보내 클라이언트가 이후 이벤트를 추적할 수 있게 한다.
        yield _sse({
            "event": "initializing",
            "msg": "보고서 생성을 시작합니다.",
            "rid": rid,
        })

        session = await create_initial_session(db, req)

        # 유저 질의를 세션 chat_logs 에 남겨 대화형 재생성/이력 UI 가 참조.
        session.chat_logs.append(doc.ChatMessage(role="user", content=req.query, rid=rid))
        await db.save(session)

        # --- Stage: planning ---
        yield _sse({"event": "planning", "msg": "보고서 plan 작성 중…", "rid": rid})

        api_tools = list(req.tools or [])
        plan_kwargs: dict = {
            "data_id": req.did,
            "query": req.query,
            "tools": api_tools,
        }
        if req.description:
            plan_kwargs["description"] = req.description
        plan: ReportPlanOutput = await nodes.nodes["report/plan"].run(**plan_kwargs)
        # API tools 와 데이터셋 기본 툴을 plan.tools / task.tools 에 정규화.
        # (누락·중복 경로가 후속 codegen 컨텍스트를 깨뜨리지 않게)
        plan = finalize_plan_tools(plan, api_tools, data_id=req.did)

        # --- Stage: planned 직전 persist ---
        # status="planned": codegen 전에도 rid 로 목록에 보이게 하고,
        # 중도 실패 시 failed 로 덮어쓸 수 있는 앵커 문서를 먼저 만든다.
        report_doc = doc.Report(
            rid=rid,
            plan_id=plan.plan_id,
            session_id=session.session_id,
            did=req.did,
            title=plan.title,
            query=req.query,
            description=req.description,
            tools=api_tools,
            version=len(session.report_stack) + 1,
            status="planned",
        )

        plan_doc = doc.Plan(
            plan_id=plan.plan_id,
            rid=rid,
            session_id=session.session_id,
            title=plan.title,
            blueprint=plan.model_dump(),
            tools=plan.tools,
        )
        # Plan 과 Report 를 동시 저장 — 한쪽만 있으면 update/exec 가 깨짐.
        await asyncio.gather(db.save(plan_doc), db.save(report_doc))

        # 디스크 쪽 plan.json / srcs 디렉토리 — runner 가 파일 기준으로도 동작.
        ensure_report_dirs(rid)
        save_plan(rid, plan)
        data = await db.get(req.did)

        task_summary = ", ".join(f"{t.type}:{t.title}" for t in plan.tasks)
        yield _sse({
            "event": "planned",
            "msg": f"설계 완료: {plan.title} — 태스크 {len(plan.tasks)}개 ({task_summary})",
            "rid": rid,
            "data": data,
            "result": plan.model_dump(mode="json"),
        })

        # --- Stage: task codegen + execute ---
        # ctx: 태스크 간 board/공유 상태. persist_jobs: SSE 와 DB 저장 디커플.
        ctx = task_context_for_report(
            rid,
            plan.plan_id,
            plan_task_ids=[t.task_id for t in plan.tasks],
        )
        persist_jobs: list[asyncio.Task] = []
        async for ev in iter_plan_tasks(plan, ctx, rid=rid):
            if ev["event"] == "executed":
                out: TaskOutput = ev["codegen"]
                task_id = ev["task_id"]
                board = ev.get("result")
                yield _sse(ev)
                # DB 저장은 SSE 스트림을 막지 않도록 백그라운드 task 로 분리
                persist_jobs.append(asyncio.create_task(
                    _handle_executed_event(db, session, plan, task_id, out, board, rid)
                ))
            else:
                # generating / progress 등 — 클라이언트로 그대로 중계
                yield _sse(ev)

        # 모든 persist 완료 후에야 completed — 클라이언트가 목록 API 를 치면 일관.
        if persist_jobs:
            await asyncio.gather(*persist_jobs)

        # --- Stage: collect + completed ---
        usage = current_usage()
        usage_dict = usage.to_dict() if usage else None
        report_result = collect_report_result(
            plan,
            ctx,
            rid,
            generation_started_at=generation_started_at,
            generation_duration_sec=time.perf_counter() - generation_started_perf,
            llm_usage=usage_dict,
        )
        usage_brief = ""
        if usage_dict:
            persist_report_usage_log(rid, usage_dict)
            usage_brief = format_usage_brief(usage_dict)
        report_doc.status = "completed"
        await db.save(report_doc)
        session.current_rid = rid
        if rid not in session.report_stack:
            session.report_stack.append(rid)
        session.chat_logs.append(doc.ChatMessage(
            role="assistant",
            content=f"'{report_doc.title}' 보고서 작성이 완료되었습니다.",
            rid=rid,
        ))
        await db.save(session)

        completed_msg = (
            f"보고서 작성 완료 — {usage_brief}" if usage_brief else "보고서 작성 완료"
        )
        yield _sse({
            "event": "completed",
            "msg": completed_msg,
            "rid": rid,
            "usage": usage_dict,
            "result": {
                "rid": rid,
                "plan_id": plan.plan_id,
                "title": plan.title,
                **_client_report_payload(report_result),
                "usage": usage_dict,
            },
        })
        log_console_brief(f"SUCCESS rid={rid}")

    except LLMTimeoutError as e:
        if report_doc:
            report_doc.status = "failed"
            await db.save(report_doc)
        err_msg = e.message
        error(err_msg)
        yield _sse({
            "event": "failed",
            "msg": f"LLM timeout: {e.message}",
            "rid": rid,
            "error": err_msg,
            "phase": "llm_timeout",
        })
    except QuotaExceededError as e:
        if report_doc:
            report_doc.status = "failed"
            await db.save(report_doc)
        err_msg = e.message
        error(err_msg)
        yield _sse({
            "event": "failed",
            "msg": f"LLM API 한도 초과: {e.message}",
            "rid": rid,
            "error": err_msg,
            "phase": "llm_quota",
        })
    except ContextAttachTooLargeError as e:
        if report_doc:
            report_doc.status = "failed"
            await db.save(report_doc)
        err_msg = e.message
        error(err_msg)
        yield _sse({
            "event": "failed",
            "msg": e.message,
            "rid": rid,
            "error": err_msg,
            "phase": "context_attach_limit",
        })
    except MaxRetriesExceededError as e:
        if report_doc:
            report_doc.status = "failed"
            await db.save(report_doc)
        err_msg = e.last_error or traceback.format_exc()
        error(err_msg)
        yield _sse({
            "event": "failed",
            "msg": f"중단됨: {e.message}",
            "rid": rid,
            "error": err_msg,
            "phase": "codegen",
        })
    except Exception as e:
        if report_doc:
            report_doc.status = "failed"
            await db.save(report_doc)
        err_msg = traceback.format_exc()
        error(err_msg)
        yield _sse({"event": "failed", "msg": f"중단됨: {str(e)}", "rid": rid, "error": err_msg})
    finally:
        reset_report_generation()
        close_report_log()


async def handle_report_execution(rid: str, db: SAGEDataStore):
    """Execute a published report's saved task sources and persist run artifacts.

    Args:
        rid: Report id (must be ``published`` with complete ``srcs/*.py``).
        db: Store for Report/Plan lookup.

    Yields:
        SSE payloads via :class:`~routers.base.SSEEncoder` through run completion
        or error (missing sources, non-published status, execution failure).
    """
    # ==================================================================
    # Publish 게이트 설계
    # - generate/update 완료 상태는 completed. exec 는 "발행된 확정본"만
    #   돌리도록 published 를 강제한다. 이유:
    #   (1) 초안/실패본이 운영 스케줄에 잘못 올라가는 것 방지
    #   (2) publish API 가 사람이 검토한 뒤의 명시적 승낙 스위치
    # - 추가로 srcs/*.py 완전성 검사: published 여도 codegen 산출물이
    #   없으면 runner 가 중간에 죽으므로 선제 거부.
    # - 실행 산출물은 reports 원본을 덮지 않고 run_dir 에 분리 저장
    #   (재실행 이력·롤백용).
    # ==================================================================
    run_id: str | None = None
    run_dir: Path | None = None
    started_at = datetime.now(timezone.utc)

    try:
        yield SSEEncoder.encode("initializing", "보고서 실행을 시작합니다.", rid=rid)

        report_doc = await db.load(doc.Report, rid)
        if not report_doc:
            yield SSEEncoder.encode("error", f"리포트를 찾을 수 없습니다: {rid}", rid=rid)
            return

        # Publish gate — completed/planned/failed 등은 여기서 차단.
        if report_doc.status != "published":
            yield SSEEncoder.encode(
                "error",
                f"보고서 실행은 published 상태에서만 가능합니다. (현재: {report_doc.status})",
                rid=rid,
            )
            return

        plan_doc = await db.load(doc.Plan, report_doc.plan_id)
        try:
            # 디스크 plan 우선, DB blueprint 폴백 — 파일 기준 실행과 동기화.
            plan = load_plan_from_report(rid, db_plan=plan_doc)
        except FileNotFoundError as exc:
            yield SSEEncoder.encode("error", str(exc), rid=rid)
            return

        # 태스크별 executor 소스 누락 시 부분 실행보다 명확한 에러가 낫다.
        missing = missing_task_sources(rid, plan)
        if missing:
            yield SSEEncoder.encode(
                "error",
                f"태스크 executor 소스 없음 (reports/{rid}/srcs/): {', '.join(missing)}",
                rid=rid,
            )
            return

        # run_id/run_dir: 이번 실행만의 아티팩트 루트 (원본 srcs 와 분리).
        run_id, run_dir = make_run_dir()
        save_run_meta(
            run_dir,
            run_id=run_id,
            rid=rid,
            plan_id=plan.plan_id,
            status="running",
            started_at=started_at,
        )

        data = await db.get(report_doc.did)
        yield SSEEncoder.encode(
            "planned",
            f"실행 준비: {plan.title}",
            rid=rid,
            run_id=run_id,
            data=data,
            result=plan.model_dump(mode="json"),
        )

        ctx = task_context_for_report(
            rid,
            plan.plan_id,
            plan_task_ids=[t.task_id for t in plan.tasks],
        )

        # iter_report_exec: codegen 없이 저장된 소스만 실행 (생성 파이프라인과 대칭).
        async for ev in iter_report_exec(plan, ctx, rid=rid, run_dir=run_dir):
            event = ev.pop("event")
            msg = ev.pop("msg")
            rid = ev.pop("rid")
            yield SSEEncoder.encode(event, msg, rid=rid, run_id=run_id, **ev)

        # artifact_dir=run_dir — 생성 시 draft 와 달리 이번 런 폴더에 결과 수집.
        exec_result = collect_report_result(
            plan,
            ctx,
            rid,
            generation_started_at=started_at,
            artifact_dir=run_dir,
        )

        save_run_meta(
            run_dir,
            run_id=run_id,
            rid=rid,
            plan_id=plan.plan_id,
            status="completed",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )

        yield SSEEncoder.encode(
            "completed",
            "보고서 실행이 완료되었습니다.",
            rid=rid,
            run_id=run_id,
            data=data,
            result=_client_report_payload(exec_result),
        )

    except Exception as exc:
        err_msg = traceback.format_exc()
        error(err_msg)
        if run_dir is not None and run_id is not None:
            plan_id = plan.plan_id if "plan" in locals() else (report_doc.plan_id if report_doc else "")
            save_run_meta(
                run_dir,
                run_id=run_id,
                rid=rid,
                plan_id=plan_id,
                status="failed",
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                error=str(exc),
            )
        yield SSEEncoder.encode("failed", f"실행 중단: {exc}", rid=rid, run_id=run_id, error=err_msg)


async def handle_report_update(req: ReportUpdateRequest, db: SAGEDataStore):
    """Regenerate and re-run selected plan tasks and their downstream dependents.

    Args:
        req: Update request with ``rid``, ``task_ids``, optional ``query`` / ``tools``.
        db: Store for Report, Plan, Session, and Task persistence.

    Yields:
        SSE payloads via :func:`_sse` through partial regen and final ``completed`` / ``failed``.
    """
    # ==================================================================
    # DAG closure (부분 재생성) 왜 필요한가?
    # - 사용자는 보통 "이 태스크만 고치자"고 요청하지만, 보고서 태스크는
    #   선행 board/컨텍스트에 의존하는 DAG 이다.
    # - 선택 태스크만 고치고 downstream 을 안 돌리면 오래된 아티팩트가
    #   남거나 narrative/release 가 stale context 를 읽는다.
    # - 따라서 downstream_task_closure 로 (요청 ∪ 후속의존) 집합을 계산한 뒤
    #   only_tasks=rerun_ids 로 iter_plan_tasks 에 넘긴다.
    # - 플랜에 없는 task_id 는 hard-fail 대신 무시: 구버전 UI id 혼선 대비.
    # ==================================================================
    rid = req.rid
    report_doc = None
    report_log = open_report_log(rid)
    log_report_log_link(rid, report_log)
    generation_started_at = datetime.now(timezone.utc)
    generation_started_perf = time.perf_counter()
    begin_report_generation()

    try:
        report_doc = await db.load(doc.Report, rid)
        if not report_doc:
            yield _sse({"event": "failed", "msg": "보고서를 찾을 수 없습니다.", "rid": rid})
            return

        yield _sse({
            "event": "initializing",
            "msg": f"보고서 업데이트 시작 (v{report_doc.version})",
            "rid": rid,
        })

        plan_doc = await db.load(doc.Plan, report_doc.plan_id)
        if not plan_doc:
            yield _sse({"event": "failed", "msg": "플랜을 찾을 수 없습니다.", "rid": rid})
            return

        plan = load_plan_from_report(rid, db_plan=plan_doc)
        # 요청 seed → transitive downstream 닫힘(closure).
        rerun_ids = downstream_task_closure(plan.tasks, set(req.task_ids))
        unknown = set(req.task_ids) - {t.task_id for t in plan.tasks}
        if unknown:
            warning(f"update_report: plan 에 없는 task_id 무시: {unknown}")

        task_titles = [
            t.title for t in plan.tasks if t.task_id in rerun_ids
        ]
        yield _sse({
            "event": "updating",
            "msg": (
                f"재생성·실행 대상 {len(rerun_ids)}개 "
                f"(요청 {len(req.task_ids)} + downstream): {', '.join(task_titles)}"
            ),
            "rid": rid,
            "task_ids": sorted(rerun_ids),
        })

        # 세션이 끊긴 구 리포트도 업데이트가 가능하게 orphan session 재생성.
        session = None
        if report_doc.session_id:
            session = await db.load(doc.Session, report_doc.session_id)
        if session is None:
            session = doc.Session(
                session_id=f"sess-{uuid.uuid4().hex[:8]}",
                title_query=req.query,
            )
            await db.save(session)
            report_doc.session_id = session.session_id
            await db.save(report_doc)

        ctx = task_context_for_report(
            rid,
            plan.plan_id,
            plan_task_ids=[t.task_id for t in plan.tasks],
        )
        api_tools = list(req.tools or [])

        persist_jobs: list[asyncio.Task] = []
        # only_tasks: closure 바깥은 스킵해 비용 절감.
        # instruction_extra=req.query: 부분 수정 지침을 codegen 에만 추가 주입.
        async for ev in iter_plan_tasks(
                plan,
                ctx,
                rid=rid,
                tools=api_tools,
                only_tasks=rerun_ids,
                instruction_extra=req.query,
        ):
            if ev["event"] == "executed":
                out: TaskOutput = ev["codegen"]
                task_id = ev["task_id"]
                board = ev.get("result")
                yield _sse(ev)
                persist_jobs.append(asyncio.create_task(
                    _handle_executed_event(db, session, plan, task_id, out, board, rid)
                ))
            else:
                yield _sse(ev)

        if persist_jobs:
            await asyncio.gather(*persist_jobs)

        usage = current_usage()
        usage_dict = usage.to_dict() if usage else None
        # 부분 재생성 후에도 draft/report 전체를 다시 수집 — downstream
        # 산출물이 바뀌었을 때 단일 아티팩트로 UI 에 내려주기 위함.
        report_result = collect_report_result(
            plan,
            ctx,
            rid,
            generation_started_at=generation_started_at,
            generation_duration_sec=time.perf_counter() - generation_started_perf,
            llm_usage=usage_dict,
        )
        usage_brief = ""
        if usage_dict:
            persist_report_usage_log(rid, usage_dict)
            usage_brief = format_usage_brief(usage_dict)

        # version bump: 같은 rid 유지하면서 "수정본"을 표시. 새 rid 를
        # 만들지 않는 이유 — 링크·세션·디스크 경로 연속성 유지.
        report_doc.version += 1
        report_doc.status = "completed"
        await db.save(report_doc)

        if session:
            session.chat_logs.append(doc.ChatMessage(
                role="user",
                content=req.query,
                rid=rid,
            ))
            session.chat_logs.append(doc.ChatMessage(
                role="assistant",
                content=f"'{report_doc.title}' 보고서 {len(rerun_ids)}개 단계가 수정되었습니다.",
                rid=rid,
            ))
            await db.save(session)

        update_msg = (
            f"보고서 수정 작업이 완료되었습니다 — {usage_brief}"
            if usage_brief
            else "보고서 수정 작업이 완료되었습니다."
        )
        yield _sse({
            "event": "completed",
            "msg": update_msg,
            "rid": rid,
            "usage": usage_dict,
            "result": {
                "rid": rid,
                "version": report_doc.version,
                "updated_tasks": sorted(rerun_ids),
                **_client_report_payload(report_result),
                "usage": usage_dict,
            },
        })
        log_console_brief(f"UPDATE SUCCESS rid={rid}")

    except LLMTimeoutError as e:
        if report_doc:
            report_doc.status = "failed"
            await db.save(report_doc)
        err_msg = e.message
        error(err_msg)
        yield _sse({
            "event": "failed",
            "msg": f"LLM timeout: {e.message}",
            "rid": rid,
            "error": err_msg,
            "phase": "llm_timeout",
        })
    except QuotaExceededError as e:
        if report_doc:
            report_doc.status = "failed"
            await db.save(report_doc)
        err_msg = e.message
        error(err_msg)
        yield _sse({
            "event": "failed",
            "msg": f"LLM API 한도 초과: {e.message}",
            "rid": rid,
            "error": err_msg,
            "phase": "llm_quota",
        })
    except ContextAttachTooLargeError as e:
        if report_doc:
            report_doc.status = "failed"
            await db.save(report_doc)
        err_msg = e.message
        error(err_msg)
        yield _sse({
            "event": "failed",
            "msg": e.message,
            "rid": rid,
            "error": err_msg,
            "phase": "context_attach_limit",
        })
    except MaxRetriesExceededError as e:
        if report_doc:
            report_doc.status = "failed"
            await db.save(report_doc)
        err_msg = e.last_error or traceback.format_exc()
        error(err_msg)
        yield _sse({
            "event": "failed",
            "msg": f"중단됨: {e.message}",
            "rid": rid,
            "error": err_msg,
            "phase": "codegen",
        })
    except Exception as e:
        if report_doc:
            report_doc.status = "failed"
            await db.save(report_doc)
        err_msg = traceback.format_exc()
        error(err_msg)
        yield _sse({"event": "failed", "msg": f"업데이트 중 오류: {str(e)}", "rid": rid, "error": err_msg})
    finally:
        # generate 과 동일: ContextVar/파일 핸들 누수 방지.
        reset_report_generation()
        close_report_log()
