"""Pre-LLM prompt size logging — cutoff verification and report log dump."""

from __future__ import annotations

import json
import os
from typing import Any

from sage.llm.pricing import estimate_prompt_input_tokens, estimate_tokens_from_chars
from sage.logg import append_report_log, info, warning
from sage.report.context_limits import json_payload_byte_size

LLM_ATTACH_MAX_BYTES = int(os.environ.get("SAGE_LLM_ATTACH_MAX_BYTES", "262144"))
LLM_ATTACH_RELEASE_MAX_BYTES = int(
    os.environ.get("SAGE_LLM_ATTACH_RELEASE_MAX_BYTES", "524288")
)


def _attach_limit(task_type: str | None) -> int:
    if (task_type or "").strip() == "release":
        return LLM_ATTACH_RELEASE_MAX_BYTES
    return LLM_ATTACH_MAX_BYTES


def log_prompt_before_llm(
    *,
    node_path: str | None,
    attempt: int,
    llm_type: str,
    model: str,
    task_type: str | None,
    system: str,
    user: str,
    feedback: str = "",
    attach: dict[str, Any] | None = None,
    extra_messages: int = 0,
) -> None:
    """Log prompt budget summary (INFO) and full prompt body (report log)."""
    sys_chars = len(system or "")
    user_chars = len(user or "")
    fb_chars = len(feedback or "")
    prompt_chars = sys_chars + user_chars + fb_chars
    attach_bytes = json_payload_byte_size(attach) if attach else 0
    est_text = estimate_tokens_from_chars(prompt_chars)
    est_attach = estimate_tokens_from_chars(attach_bytes)
    est_in = estimate_prompt_input_tokens(
        prompt_chars=prompt_chars,
        attach_bytes=attach_bytes,
    )

    limit = _attach_limit(task_type)
    attach_pct = (attach_bytes / limit * 100.0) if limit else 0.0

    site = node_path or "?"
    summary = (
        f"[prompt] {site} try={attempt + 1} llm={llm_type}/{model} "
        f"task_type={task_type or '-'} "
        f"chars=sys:{sys_chars} user:{user_chars} fb:{fb_chars} total:{prompt_chars} "
        f"est_in≈{est_in} (text≈{est_text}+attach≈{est_attach}) "
        f"attach={attach_bytes}B/{limit}B ({attach_pct:.1f}%) billed "
        f"extra_msgs={extra_messages}"
    )
    info(summary)
    append_report_log(summary)

    if attach_bytes > limit:
        warning(
            f"[prompt] attach exceeds limit: {attach_bytes} > {limit} "
            f"(task_type={task_type!r}, site={site})"
        )

    divider = "=" * 72
    attach_preview = ""
    if attach:
        try:
            attach_preview = json.dumps(attach, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            attach_preview = repr(attach)

    body_parts = [
        divider,
        f"PROMPT FULL DUMP — {site} attempt={attempt + 1}",
        divider,
        "--- SYSTEM ---",
        system or "",
        "--- USER ---",
        user or "",
    ]
    if feedback:
        body_parts.extend(["--- RETRY FEEDBACK ---", feedback])
    if attach_preview:
        body_parts.extend([
            f"--- LLM_ATTACH ({attach_bytes} bytes, limit {limit}) ---",
            attach_preview,
        ])
    body_parts.append(divider)

    full_block = "\n".join(body_parts)
    append_report_log(full_block)
