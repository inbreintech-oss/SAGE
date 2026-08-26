"""
p2 NodeV LLM 입력 enrich.

EnrichRule: trigger(Input 필드) → target(LLM prompt 필드) + enricher
  - target == trigger  : 값 교체 (tools path → spec)
  - target != trigger  : 필드 추가 (data_id → dataset_context, plan_id → 칠판 전체)

Input 모델에 trigger 필드가 있으면 enrich 실행.
TaskCodegenInput: llm_attach — upstream json payload (집계·선별). release: + upstream_sources
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Type

from pydantic import BaseModel
from utils.conv import sanitize_tree

from sage.errs import ContextAttachTooLargeError, ContextStorageError
from sage.llm.llms import validate_llm_attach
from sage.report.context import TaskContext
from sage.report.plan_tools import resolve_report_tool_paths
from sage.prompt.dataset import load_schema
from sage.prompt.report_prompts import (
    load_domain_brief,
    load_runtime_contract,
    should_inject_domain_brief,
)
from sage.report.codegen_contract import DATASET_CONTEXT_FOOTNOTE

EnrichFn = Callable[["EnrichRule", "EnrichContext"], Awaitable[Any]]

async def tools_spec_for_llm(
    tools: list[str] | None,
    *,
    data_id: str | None = None,
) -> list[str]:
    """MCP tool path merge 후 list_tools spec JSON (LLM prompt 용)."""
    from sage.mcp import load_tools_spec

    paths = resolve_report_tool_paths(tools, data_id=data_id)
    return await load_tools_spec(paths) if paths else []

@dataclass(frozen=True)
class EnrichRule:
    trigger: str
    target: str
    label: str
    enricher: str
    aliases: tuple[str, ...] = field(default_factory=tuple)

@dataclass
class EnrichContext:
    kwargs: dict[str, Any]
    input_model: Type[BaseModel]

    def data_id(self) -> str | None:
        v = self.kwargs.get("data_id") or self.kwargs.get("did")
        return v if v else None

ENRICH_RULES: tuple[EnrichRule, ...] = (
    EnrichRule(
        trigger="data_id",
        target="dataset_context",
        label="Pangea 스키마·프로파일",
        enricher="dataset_context",
        aliases=("did",),
    ),
    EnrichRule(
        trigger="tools",
        target="tools",
        label="",
        enricher="tools_spec",
    ),
    EnrichRule(
        trigger="plan_id",
        target="upstream_context",
        label="TaskContext 칠판 (현재까지)",
        enricher="task_upstream",
    ),
    EnrichRule(
        trigger="plan_id",
        target="runtime_contract",
        label="Task executor runtime contract",
        enricher="runtime_contract",
    ),
    EnrichRule(
        trigger="plan_id",
        target="domain_brief",
        label="Domain brief (optional)",
        enricher="domain_brief",
    ),
)

async def _dataset_context(rule: EnrichRule, ctx: EnrichContext) -> str:
    data_id = ctx.data_id()
    if not data_id:
        return ""
    body = await load_schema(data_id)
    return f"{body}{DATASET_CONTEXT_FOOTNOTE}" if body.strip() else ""

async def _tools_spec(rule: EnrichRule, ctx: EnrichContext) -> str:
    import json

    value = ctx.kwargs.get(rule.trigger) or []
    specs = await tools_spec_for_llm(list(value), data_id=ctx.data_id())
    if not specs:
        return "(등록된 MCP 도구 없음 — call() 사용 금지)"

    names: list[str] = []
    for block in specs:
        try:
            for tool in json.loads(block):
                tp = tool.get("tool_path", "")
                nm = tool.get("name", "")
                if not nm:
                    continue
                props = list((tool.get("input") or {}).get("properties", {}).keys())
                arg_hint = f"({', '.join(props)})" if props else "()"
                names.append(f"{tp}/{nm}{arg_hint}" if tp else f"{nm}{arg_hint}")
        except json.JSONDecodeError:
            continue

    # 보고서 plan/task codegen 만 prelude 주입. /tool/exec·generate caller 는 직접 import.
    prelude = ctx.input_model.__name__ in ("TaskCodegenInput", "ReportPlanInput")
    catalog = ", ".join(names) if names else "(파싱 실패 — spec JSON 확인)"
    if prelude:
        header = (
            "call(path, name, args) — spec 의 path·name·input.properties 만. "
            "call 은 prelude 주입, body 에 import 작성 금지.\n"
            f"등록: {catalog}\n"
        )
    else:
        header = (
            "call(path, name, args) — spec 의 path·name·input.properties. "
            "`from sage.mcp import call`. kwargs['call'] 없음.\n"
            f"등록: {catalog}\n"
        )
    return header + "\n\n".join(specs)

def _build_upstream_payloads(task_ctx: TaskContext, board_ids: list[str]) -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    for tid in board_ids:
        info = task_ctx.tasks.get(tid)
        if not info:
            continue
        keys: dict[str, Any] = {}
        for key, res in info.results.items():
            if res.type != "json":
                raise ContextStorageError(
                    f"upstream_payloads: legacy {res.type!r} key {tid}/{key} — "
                    "context는 json(dict/list)만 llm_attach 가능."
                )
            keys[key] = sanitize_tree(task_ctx.get_result(tid, key))
        if keys:
            payloads[tid] = {"status": info.status, "keys": keys}
    return payloads

def _load_upstream_sources(rid: str, board_ids: list[str]) -> dict[str, str]:
    from sage.report.task_sources import report_srcs_dir

    sources: dict[str, str] = {}
    src_dir = report_srcs_dir(rid)
    for tid in board_ids:
        path = src_dir / f"{tid}.py"
        if path.is_file():
            sources[tid] = path.read_text(encoding="utf-8")
    return sources

def _upstream_access_hints(task_ctx: TaskContext, context_ids: list[str]) -> str:
    """task.context upstream + 칠판 catalog key (runtime 과 align)."""
    if not context_ids:
        return ""
    full_board = task_ctx.catalog()
    lines = [
        "[upstream 접근 — task.context DAG edge + 칠판 catalog key]",
        "task.context[i] 로 upstream task_id — 하드코딩 금지.",
        "",
    ]
    for i, tid in enumerate(context_ids):
        info = full_board.get(tid)
        if not info:
            lines.append(f"task.context[{i}]  # {tid!r} (아직 칠판 없음)")
            continue
        keys = list((info.get("keys") or {}).keys())
        lines.append(f"task.context[{i}]  # {tid}: {keys or '(key 없음)'}")
        for key in keys:
            lines.append(f'  ctx.get_result(task.context[{i}], "{key}")')
        lines.append("")

    other = [
        (tid, list((info.get("keys") or {}).keys()))
        for tid, info in full_board.items()
        if tid not in context_ids and info.get("keys")
    ]
    if other:
        lines.append("# task.context 외 칠판 (visual 등 — catalog key 참고):")
        for tid, keys in other:
            lines.append(f"- {tid}: {keys}")
    return "\n".join(lines).rstrip()

def _plan_board_ids(task_ctx: TaskContext, plan_task_ids: list[str]) -> list[str]:
    """plan.tasks 에 속한 칠판 task_id 만 — stale·orphan 제외."""
    if not plan_task_ids:
        return list(task_ctx.tasks.keys())
    allowed = set(plan_task_ids)
    return [tid for tid in task_ctx.tasks.keys() if tid in allowed]


async def _task_upstream(rule: EnrichRule, ctx: EnrichContext) -> str:
    plan_id = ctx.kwargs.get("plan_id")
    if not plan_id:
        return ""
    plan_task_ids = list(ctx.kwargs.get("plan_task_ids") or [])
    task_ctx = TaskContext.load(
        plan_id,
        rid=ctx.kwargs.get("rid"),
        plan_task_ids=plan_task_ids or None,
    )
    task_type = ctx.kwargs.get("type")
    header = ""
    if task_type == "release":
        from sage.report.release_contract import RELEASE_ATTACH_USAGE, RELEASE_CODEGEN_STEPS

        header = (
            "release llm_attach: upstream_payloads(report_document 포함) + upstream_sources.\n"
            f"{RELEASE_CODEGEN_STEPS}\n"
            f"{RELEASE_ATTACH_USAGE}\n\n"
        )
    compact = bool(task_type)
    body = (
        task_ctx.to_llm_catalog_compact()
        if compact
        else task_ctx.to_llm_prompt()
    )
    hints = _upstream_access_hints(task_ctx, list(ctx.kwargs.get("context") or []))
    if hints:
        body = f"{body}\n\n{hints}"
    return header + body

async def _runtime_contract(rule: EnrichRule, ctx: EnrichContext) -> str:
    task_type = ctx.kwargs.get("type")
    if not task_type:
        return ""
    return load_runtime_contract(str(task_type))

async def _data_category(data_id: str | None) -> str | None:
    if not data_id:
        return None
    try:
        from sage.db import saged

        doc = await saged.get(data_id)
        if doc is None:
            return None
        if isinstance(doc, dict):
            return doc.get("category")
        return getattr(doc, "category", None)
    except Exception:
        return None

async def _domain_brief(rule: EnrichRule, ctx: EnrichContext) -> str:
    if ctx.kwargs.get("type") != "narrative":
        return ""
    category = await _data_category(ctx.data_id())
    if not should_inject_domain_brief(
        user_description=ctx.kwargs.get("user_description"),
        report_query=ctx.kwargs.get("report_query"),
        data_category=category,
    ):
        return ""
    return load_domain_brief(category)


async def _task_llm_attach(ctx: EnrichContext) -> dict[str, Any]:
    """TaskCodegenInput 공통: plan 칠판 payload. release 는 upstream_sources 추가."""
    plan_id = ctx.kwargs.get("plan_id")
    rid = ctx.kwargs.get("rid")
    task_type = ctx.kwargs.get("type")
    plan_task_ids = list(ctx.kwargs.get("plan_task_ids") or [])
    if not plan_id or not task_type:
        return {}

    task_ctx = TaskContext.load(
        plan_id,
        rid=rid,
        plan_task_ids=plan_task_ids or None,
    )
    board_ids = _plan_board_ids(task_ctx, plan_task_ids)
    payloads = _build_upstream_payloads(task_ctx, board_ids)
    if not payloads and task_type != "release":
        return {}

    attach: dict[str, Any] = {"upstream_payloads": payloads}

    if task_type == "release":
        if rid and board_ids:
            sources = _load_upstream_sources(rid, board_ids)
            if sources:
                attach["upstream_sources"] = sources

    validate_llm_attach(attach, task_type=task_type)
    return attach


ENRICHERS: dict[str, EnrichFn] = {
    "dataset_context": _dataset_context,
    "tools_spec": _tools_spec,
    "task_upstream": _task_upstream,
    "runtime_contract": _runtime_contract,
    "domain_brief": _domain_brief,
}

def _trigger_in_model(rule: EnrichRule, fields: set[str]) -> bool:
    return rule.trigger in fields or any(a in fields for a in rule.aliases)

def resolve_rules(input_model: Type[BaseModel]) -> list[EnrichRule]:
    """Input 모델에 trigger 필드가 있으면 해당 enrich 규칙 적용."""
    fields = set(input_model.model_fields.keys())
    return [rule for rule in ENRICH_RULES if _trigger_in_model(rule, fields)]

async def apply_enrich(
    kwargs: dict[str, Any],
    input_model: Type[BaseModel],
) -> dict[str, Any]:
    out = dict(kwargs)
    ctx = EnrichContext(kwargs=out, input_model=input_model)

    for rule in resolve_rules(input_model):
        enricher = ENRICHERS.get(rule.enricher)
        if enricher is None:
            raise ValueError(f"Unknown enricher {rule.enricher!r} for rule {rule}")
        out[rule.target] = await enricher(rule, ctx)

    if out.get("plan_id") and out.get("type"):
        attach = await _task_llm_attach(ctx)
        if attach:
            out["llm_attach"] = attach

    return out

def is_added_target(target: str, input_model: Type[BaseModel]) -> bool:
    return target not in input_model.model_fields

def llm_prompt_fields(
    kwargs: dict[str, Any],
    input_model: Type[BaseModel],
) -> list[tuple[str, str, Any]]:
    rules = resolve_rules(input_model)
    added = [r for r in rules if is_added_target(r.target, input_model) and r.target in kwargs]

    parts: list[tuple[str, str, Any]] = []
    for name, field_info in input_model.model_fields.items():
        label = field_info.description or name
        val = kwargs.get(name, field_info.default)
        if val is None:
            continue
        parts.append((name, label, val))
    for rule in added:
        if rule.target in ("llm_attach",):
            continue
        val = kwargs.get(rule.target)
        if rule.target == "domain_brief" and not val:
            continue
        parts.append((rule.target, rule.label, val))
    return parts
