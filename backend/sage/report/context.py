"""TaskContext — 리포트 태스크 간 결과 공유 「칠판」(JSON only).

저장 위치:
  ``cfg.dump_path / {sha256(plan_id)[:16]} / context.json``
  reports/{rid}/srcs 와 물리적으로 분리 — 같은 plan_id 면 rid 가 달라도 칠판 공유.

계약:
  - value 는 dict/list JSON 만 (집계·통계·선별). DataFrame/parquet/csv 금지.
  - key 당 크기·shape 제한은 sage.llm.llms 의 CONTEXT_JSON_* 상수.
  - get_result 는 값 전체, catalog 는 key/description 메타만 (SSE·프롬프트용).

프롬프트 뷰:
  - to_llm_prompt: key + shape hints (attach 없을 때)
  - to_llm_catalog_compact: key 목록만 (llm_attach 에 payload 가 있을 때)
"""

import hashlib
import json
import os
import shutil
from pathlib import Path

import cfg
import pandas as pd
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

from sage.errs import ContextStorageError
from sage.report.context_limits import CONTEXT_JSON_MAX_BYTES, validate_context_json_value

CONTEXT_FILENAME = "context.json"
JSON_TYPES = frozenset({"json", "Json"})
LEGACY_FILE_TYPES = frozenset({"parquet", "csv"})


def plan_id_to_hex(plan_id: str) -> str:
    """plan_id → 저장 디렉토리용 고유 키."""
    return hashlib.sha256(plan_id.encode()).hexdigest()[:16]


def infer_data_type(value: Any) -> str:
    """data_type 미지정 시 value 타입으로 저장 형식을 추론합니다."""
    if isinstance(value, pd.DataFrame):
        raise ContextStorageError(
            "TaskContext에 DataFrame 직접 저장 금지 — "
            "통계·집계·선별 결과를 dict/list(JSON)로 변환 후 update_task 하세요."
        )
    if isinstance(value, (dict, list)):
        return "json"
    raise ContextStorageError(
        "TaskContext value는 dict/list(JSON)만 허용 — "
        "raw 표·parquet/csv·전체 row list 저장 금지."
    )


class TaskResult(BaseModel):
    type: str  # 'json' (신규) | legacy 'parquet' | 'csv'
    value: Any  # inline JSON 또는 legacy 파일 상대 경로
    description: str = ""


class TaskInfo(BaseModel):
    status: str = "pending"
    results: Dict[str, TaskResult] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class TaskContext:
    """리포트 plan 내 태스크 간 결과 공유 저장소.

    저장: cfg.dump_path / {plan_hex}/context.json (JSON inline only)
    - dict/list 집계·통계·선별 결과만 — parquet/csv/DataFrame 금지
    """

    def __init__(
        self,
        plan_id: str,
        tasks: Optional[Dict[str, TaskInfo]] = None,
        *,
        rid: Optional[str] = None,
    ):
        self.plan_id = plan_id
        self.rid = rid
        self.tasks = tasks or {}

    @property
    def plan_hex(self) -> str:
        return plan_id_to_hex(self.plan_id)

    @property
    def storage_path(self) -> str:
        return str(Path(cfg.dump_path) / self.plan_hex)

    @property
    def context_file(self) -> str:
        """context.json 경로 (메타·JSON 결과 전체)."""
        return os.path.join(self.storage_path, CONTEXT_FILENAME)

    def _resolve_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        return os.path.join(self.storage_path, path)

    def _resolve_store(self, task_id: str, key: str, data_type: str, value: Any) -> tuple[str, Any]:
        # LLM attach·Mongo 저장 모두 JSON(dict/list)만 — raw 표·파일 참조 금지 (토큰·일관성)
        if data_type in LEGACY_FILE_TYPES or data_type in ("pd.DataFrame", "DataFrame", "parquet", "csv"):
            raise ContextStorageError(
                f"TaskContext data_type={data_type!r} 금지 — json(dict/list) 집계·선별 데이터만 저장."
            )
        if isinstance(value, pd.DataFrame):
            raise ContextStorageError(
                "DataFrame 직접 저장 금지 — mean/summary/rankings 등 dict/list 로 변환 후 저장."
            )
        if data_type in JSON_TYPES or data_type == "json":
            if not isinstance(value, (dict, list)):
                raise ContextStorageError("json type 은 dict/list 값이 필요합니다.")
            validate_context_json_value(value, key_hint=f"{task_id}/{key}")
            return "json", value
        if isinstance(value, (dict, list)):
            validate_context_json_value(value, key_hint=f"{task_id}/{key}")
            return "json", value
        raise ContextStorageError(
            f"지원하지 않는 data_type/value: {data_type!r} — json(dict/list)만 허용"
        )

    _UPDATE_TASK_RESERVED = frozenset(
        {"key", "value", "data_type", "description", "status", "results"}
    )

    def update_task(
        self,
        task_id: str,
        status: str = "success",
        results: Optional[Dict[str, TaskResult]] = None,
        *,
        key: Optional[str] = None,
        value: Any = None,
        data_type: Optional[str] = None,
        description: Optional[str] = None,
        **payload_keys: Any,
    ):
        """태스크 결과 등록 — value는 dict/list(JSON) 집계·선별·chart spec.

        호출 형태:
          1) key=..., value=... — 단일 key
          2) chart_key=<dict>, table_key=<dict>, description=... — 복수 key (kwargs)
          3) results={key: TaskResult(...)} — 일괄 merge
        """
        merged = dict(results) if results else {}

        if key is not None:
            if value is None:
                raise ValueError("key 사용 시 value 가 필요합니다.")
            resolved_type = data_type if data_type is not None else infer_data_type(value)
            store_type, val_to_store = self._resolve_store(task_id, key, resolved_type, value)
            merged[key] = TaskResult(
                type=store_type,
                value=val_to_store,
                description=description or "",
            )

        for payload_key, payload_value in payload_keys.items():
            if payload_key in self._UPDATE_TASK_RESERVED:
                raise ValueError(
                    f"update_task reserved 인자 {payload_key!r} — "
                    "key/value 형식 또는 payload key 이름을 바꾸세요."
                )
            resolved_type = infer_data_type(payload_value)
            store_type, val_to_store = self._resolve_store(
                task_id, payload_key, resolved_type, payload_value
            )
            merged[payload_key] = TaskResult(
                type=store_type,
                value=val_to_store,
                description=description or "",
            )

        if not merged:
            return

        existing_task = self.tasks.get(task_id)
        current_results = dict(existing_task.results) if existing_task else {}
        current_results.update(merged)

        if existing_task:
            existing_task.status = status
            existing_task.results = current_results
        else:
            self.tasks[task_id] = TaskInfo(status=status, results=current_results)

    def get_result(self, task_id: str, key: str) -> Optional[Any]:
        """upstream 결과 값 — 없으면 None.

        legacy parquet/csv 타입이 남아 있으면 ContextStorageError:
        옛 칠판을 읽게 두지 않고 재실행·재저장을 강제한다.
        """
        task = self.tasks.get(task_id)
        if not (task and key in task.results):
            return None

        res = task.results[key]
        if res.type in LEGACY_FILE_TYPES:
            raise ContextStorageError(
                f"legacy {res.type} key {task_id}/{key} — "
                "context는 json만 허용. 태스크를 재실행해 dict/list 로 저장하세요."
            )
        return res.value

    def catalog(self, task_ids: Optional[List[str]] = None) -> dict:
        """칠판 메타 — task/key/type/description (payload 본문 제외).

        SSE ``executed.result``, UpstreamBoardValidator, layout 부착이 사용.
        payload 를 빼는 이유: 크기·비밀값·attach 중복을 피하기 위함.
        """
        ids = task_ids if task_ids is not None else list(self.tasks.keys())
        board: Dict[str, Any] = {}
        for tid in ids:
            task = self.tasks.get(tid)
            if not task:
                continue
            board[tid] = {
                "status": task.status,
                "keys": {
                    k: {
                        "type": r.type,
                        "description": r.description,
                    }
                    for k, r in task.results.items()
                },
            }
        return board

    @staticmethod
    def _json_shape_hints(value: Any) -> list[str]:
        hints: list[str] = []
        if isinstance(value, dict):
            hints.append(f"json_keys: {list(value.keys())}")
            for sub, label in (
                ("rankings", "rankings[] fields"),
                ("price_metrics", "price_metrics[] fields"),
            ):
                rows = value.get(sub)
                if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                    hints.append(f"{label}: {list(rows[0].keys())}")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            hints.append(f"list[dict] fields: {list(value[0].keys())}")
        return hints

    def to_llm_catalog_compact(self, task_ids: Optional[List[str]] = None) -> str:
        """llm_attach 가 있을 때 — task_id·key 목록만 (payload·shape hints 생략)."""
        board = self.catalog(task_ids)
        if not board:
            return "[TaskContext key catalog]\n아직 등록된 태스크 결과 없음."
        lines = [
            "[TaskContext key catalog — llm_attach upstream_payloads 참조]",
            f"plan_id: {self.plan_id}",
            "ctx.get_result(task_id, key) — key·값은 첨부 JSON 기준.",
            "",
        ]
        for tid, info in board.items():
            keys = list((info.get("keys") or {}).keys())
            lines.append(f"- {tid} ({info['status']}): {keys or '(key 없음)'}")
        return "\n".join(lines).rstrip()

    def to_llm_prompt(self, task_ids: Optional[List[str]] = None) -> str:
        """태스크 codegen 프롬프트용 칠판 — JSON key 요약만."""
        board = self.catalog(task_ids)
        if not board:
            return "[TaskContext 칠판]\n아직 등록된 태스크 결과 없음."

        lines = [
            "[TaskContext 칠판 — JSON 집계·선별 결과만]",
            f"plan_id: {self.plan_id}",
            "ctx.get_result(task_id, key) → dict/list. parquet/csv/DataFrame 저장 금지.",
            f"key당 JSON 최대 {CONTEXT_JSON_MAX_BYTES // 1024}KB — 통계·ranking·summary 위주.",
            "",
        ]
        for tid, info in board.items():
            lines.append(f"## {tid} ({info['status']})")
            if not info["keys"]:
                lines.append("  (등록된 key 없음)")
            for key, spec in info["keys"].items():
                if spec["type"] != "json":
                    lines.append(f"  - {key} [{spec['type']}]: LEGACY — json 재저장 필요")
                    continue
                desc = spec["description"] or "(설명 없음)"
                lines.append(f"  - {key} [json]: {desc}")
                val = self.get_result(tid, key)
                if val is not None:
                    for hint in self._json_shape_hints(val):
                        lines.append(f"      {hint}")
            lines.append("")
        return "\n".join(lines).rstrip()

    def to_dict(self) -> dict:
        out = {
            "plan_id": self.plan_id,
            "tasks": {tid: task.model_dump() for tid, task in self.tasks.items()},
        }
        if self.rid:
            out["rid"] = self.rid
        return out

    def save(self):
        """메모리 칠판 → context.json (atomic 아님 — 병렬 시 ctx_lock 필수)."""
        os.makedirs(self.storage_path, exist_ok=True)
        with open(self.context_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(
        cls,
        plan_id: str,
        *,
        rid: Optional[str] = None,
        plan_task_ids: Optional[list[str]] = None,
    ) -> "TaskContext":
        """디스크에서 복원. 없거나 plan_id 불일치면 빈 칠판으로 시작.

        plan_id 불일치·rid 불일치·plan에 없는 stale task 가 있으면 빈 칠판 —
        plan_id 예시 uuid 재사용 시 이전 실행 칠판이 llm_attach 로 섞이는 것을 막는다.
        """
        context_file = Path(cfg.dump_path) / plan_id_to_hex(plan_id) / CONTEXT_FILENAME

        if not context_file.is_file():
            return cls(plan_id=plan_id, rid=rid)

        with open(context_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("plan_id") != plan_id:
            return cls(plan_id=plan_id, rid=rid)

        stored_rid = data.get("rid")
        if rid and stored_rid and stored_rid != rid:
            return cls(plan_id=plan_id, rid=rid)

        tasks = {
            tid: TaskInfo.model_validate(task_data)
            for tid, task_data in data.get("tasks", {}).items()
        }

        if plan_task_ids is not None:
            allowed = set(plan_task_ids)
            loaded = set(tasks.keys())
            if loaded and (loaded - allowed):
                return cls(plan_id=plan_id, rid=rid)

        return cls(
            plan_id=plan_id,
            tasks=tasks,
            rid=rid or stored_rid,
        )


if __name__ == "__main__":
    plan_id = "pl-stock-analysis-7f2e4b1a"
    storage = Path(cfg.dump_path) / plan_id_to_hex(plan_id)

    try:
        ctx = TaskContext(plan_id=plan_id, rid="rp-demo")
        ctx.update_task(
            "task-screen-metrics",
            key="per_stats",
            value={"mean": 20.38, "min": 9.8, "max": 32.4},
            description="전체 종목 PER mean/min/max",
        )
        ctx.update_task(
            "task-sector-aggregate",
            key="sector_rankings",
            value=[{"sector": "IT", "avg_per": 22.1}, {"sector": "Finance", "avg_per": 18.3}],
            description="섹터별 PER ranking (top-N)",
        )
        ctx.save()
        print(ctx.context_file)
        print(ctx.to_llm_prompt())
    finally:
        shutil.rmtree(storage, ignore_errors=True)
