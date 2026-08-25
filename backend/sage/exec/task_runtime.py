"""Exec worker runtime API — LLM/NodeV/control-plane import 금지.

``exec_import_shims()`` 가 ``sage.report.runner`` import 를 이 모듈로 가로챈다.
"""

from __future__ import annotations

from sage.exec.shims.runner_shim import safe_report
from sage.report.task_shell import extract_task_body
from sage.report.task_sources import task_source_path
from sage.report.upstream_sources import apply_upstream_patches, persist_task_body, read_task_body

__all__ = [
    "apply_upstream_patches",
    "apply_upstream_source_updates",
    "read_task_body",
    "safe_report",
    "task_source_path",
]


def apply_upstream_source_updates(rid: str, updates: dict[str, str]) -> dict[str, str]:
    """Release QA — upstream srcs 최종본 저장 (exec-safe compile). release codegen 에서는 patches API 권장."""
    if not updates:
        raise ValueError("apply_upstream_source_updates: updates 가 비어 있습니다.")
    saved: dict[str, str] = {}
    for task_id, code in updates.items():
        if not task_id.startswith("task-"):
            raise ValueError(f"apply_upstream_source_updates: invalid task_id {task_id!r}")
        if not code or not code.strip():
            raise ValueError(f"apply_upstream_source_updates: {task_id} 소스가 비어 있습니다.")
        body = extract_task_body(code)
        saved[task_id] = persist_task_body(rid, task_id, body, validate="compile")
    return saved
