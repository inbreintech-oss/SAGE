"""Report MCP tool path 병합 — plan/task codegen 에 넘길 tools[] 확정.

우선순위·출처:
  1. REPORT_TOOLS_DEFAULT — 프레임워크 기본 (현재 빈 리스트, 확장 포인트)
  2. API 요청 tools / plan.tools — 사용자가 명시한 MCP path
  3. dataset metadata.json 의 type=tool sources — Pangea 에 묶인 도구

태스크별 (resolve_task_tool_paths):
  - task.tools 가 있으면 그것(+metadata)만
  - type==data 이고 비어 있으면 plan.tools catalog 상속 (MCP 갱신 필요)
  - analyze/visual/… 는 비어 있으면 metadata 도구만 (잘못 call 방지)

finalize_plan_tools:
  plan 노드 직후 catalog 확정 + data 태스크 tools 누락 시 backfill.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, TYPE_CHECKING

import cfg

if TYPE_CHECKING:
    from sage.models.node import ReportPlanOutput

REPORT_TOOLS_DEFAULT: list[str] = []


def normalize_mcp_tool_path(path: str) -> str:
    """MCP route path — LLM 이 ``kis/stock/get_stock_prices`` 처럼 tool명까지 붙인 경우 축소."""
    normalized = path.strip().lstrip("/").replace("\\", "/")
    if not normalized:
        return normalized
    tools_root = Path(cfg.root_path) / "tools"
    main = tools_root / normalized.replace("/", os.sep) / "main.py"
    if main.is_file():
        return normalized
    parts = normalized.split("/")
    for n in range(len(parts) - 1, 0, -1):
        candidate = "/".join(parts[:n])
        if (tools_root / candidate.replace("/", os.sep) / "main.py").is_file():
            return candidate
    return normalized


def metadata_tool_paths(data_id: str) -> list[str]:
    """dataset metadata.json sources[] 중 type=tool 의 tool_path."""
    pangea = Path(cfg.root_path) / "data" / data_id / "pangea"
    if not pangea.is_dir():
        return []
    seen: set[str] = set()
    out: list[str] = []
    for meta_path in sorted(pangea.glob("*/metadata.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for src in meta.get("sources") or []:
            if src.get("type") != "tool":
                continue
            path = (src.get("tool_path") or "").strip()
            if path and path not in seen:
                seen.add(path)
                out.append(path)
    return out


def resolve_report_tool_paths(
    tools: List[str] | None,
    *,
    data_id: str | None = None,
) -> list[str]:
    """MCP tool path merge: REPORT_TOOLS_DEFAULT + API tools + dataset metadata."""
    seen: set[str] = set()
    out: list[str] = []
    # Pangea metadata.json 에 등록된 tool 소스도 plan/exec 에 자동 포함
    meta_paths = metadata_tool_paths(data_id) if data_id else []
    for path in [*REPORT_TOOLS_DEFAULT, *(tools or []), *meta_paths]:
        norm = normalize_mcp_tool_path(path)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def resolve_task_tool_paths(
    plan_tools: List[str] | None,
    task_tools: List[str] | None,
    *,
    task_type: str,
    data_id: str | None = None,
) -> list[str]:
    """task.tools 우선 → data 타입은 plan.tools fallback → metadata merge."""
    explicit = list(task_tools or [])
    if explicit:
        return resolve_report_tool_paths(explicit, data_id=data_id)
    # data 태스크만 plan 전체 catalog 상속 (MCP 갱신·로드용)
    if task_type == "data":
        return resolve_report_tool_paths(plan_tools, data_id=data_id)
    return resolve_report_tool_paths([], data_id=data_id)


def finalize_plan_tools(
    plan: ReportPlanOutput,
    api_tools: List[str] | None,
    *,
    data_id: str,
) -> ReportPlanOutput:
    """plan.tools catalog 확정 + data 태스크 tools 누락 시 plan.tools 로 보완."""
    catalog = resolve_report_tool_paths(plan.tools or api_tools, data_id=data_id)
    tasks = []
    for task in plan.tasks:
        if task.type == "data" and not task.tools and catalog:
            tasks.append(task.model_copy(update={"tools": catalog}))
        elif task.tools:
            tasks.append(
                task.model_copy(
                    update={"tools": resolve_report_tool_paths(task.tools, data_id=data_id)}
                )
            )
        else:
            tasks.append(task)
    return plan.model_copy(update={"tools": catalog, "tasks": tasks})
