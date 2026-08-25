"""Upstream task source read/patch/save — release QA (LLM body embed 금지)."""

from __future__ import annotations

from typing import Any

from sage.report.task_shell import assemble_task_source, extract_task_body
from sage.report.task_sources import save_task_source, task_source_path


def read_task_body(rid: str, task_id: str) -> str:
    """``srcs/{task_id}.py`` 에서 LLM body 만 추출."""
    path = task_source_path(rid, task_id)
    if not path.is_file():
        raise ValueError(f"read_task_body: 소스 없음 — {path}")
    return extract_task_body(path.read_text(encoding="utf-8"))


def persist_task_body(
    rid: str,
    task_id: str,
    body: str,
    *,
    validate: str = "compile",
) -> str:
    """body → prelude 조립 → 검증 → 디스크 저장. 저장 경로 str 반환."""
    if not task_id.startswith("task-"):
        raise ValueError(f"persist_task_body: invalid task_id {task_id!r}")
    assembled = assemble_task_source(body)
    if validate == "full":
        from sage.report.runner import validate_task_code

        validate_task_code(assembled, task_id)
    else:
        compile(assembled, f"<{task_id}>", "exec")
    return str(save_task_source(rid, task_id, assembled))


def apply_upstream_patches(
    rid: str,
    patches: dict[str, list[dict[str, Any]]],
    *,
    validate: str = "compile",
) -> dict[str, str]:
    """디스크 upstream body 를 old/new 패치 후 저장.

    ``patches[tid] == []`` — 변경 없이 read→re-validate→save (narrative 필수 refresh).
    각 op: ``{"old": "...", "new": "..."}`` — ``old`` 는 body 내 1회만 replace.
    """
    if not patches:
        raise ValueError("apply_upstream_patches: patches 가 비어 있습니다.")
    saved: dict[str, str] = {}
    for task_id, ops in patches.items():
        body = read_task_body(rid, task_id)
        for op in ops or []:
            if not isinstance(op, dict):
                raise ValueError(f"apply_upstream_patches: {task_id} op 은 dict 필요")
            old = op.get("old")
            new = op.get("new")
            if not isinstance(old, str) or not old:
                raise ValueError(f"apply_upstream_patches: {task_id} op.old 비어 있음")
            if new is None:
                new = ""
            if not isinstance(new, str):
                raise ValueError(f"apply_upstream_patches: {task_id} op.new 는 str")
            if old not in body:
                raise ValueError(
                    f"apply_upstream_patches: {task_id} op.old 가 body 에 없음 — "
                    "llm_attach upstream_sources 와 정확히 일치하는 snippet 사용"
                )
            body = body.replace(old, new, 1)
        saved[task_id] = persist_task_body(rid, task_id, body, validate=validate)
    return saved
