"""report.json generation 메타 — 작성 시각·소요·문자 수·토큰."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

def _iso_dt(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()

def _text_from_block(block_type: str, payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    parts: list[str] = []
    if block_type == "header":
        parts.append(str(payload.get("text") or ""))
    elif block_type == "card":
        parts.append(str(payload.get("title") or ""))
        parts.append(str(payload.get("content") or ""))
    elif block_type == "table":
        header = payload.get("header") or []
        parts.extend(str(h) for h in header)
        for row in payload.get("data") or []:
            if isinstance(row, (list, tuple)):
                parts.extend(str(c) for c in row)
            else:
                parts.append(str(row))
    elif block_type in ("echart", "chart"):
        title = payload.get("title")
        if isinstance(title, dict):
            parts.append(str(title.get("text") or ""))
            parts.append(str(title.get("subtext") or ""))
        elif isinstance(title, str):
            parts.append(title)
    return "\n".join(p for p in parts if p)

def count_report_text_characters(report: dict[str, Any]) -> int:
    """layout·data 에서 읽을 수 있는 본문(제목·카드·표·차트 제목) 문자 수."""
    parts = [
        str(report.get("title") or ""),
        str(report.get("description") or ""),
    ]
    layout = report.get("layout") or {}
    data = report.get("data") or {}

    def walk_blocks(blocks: list[Any]) -> None:
        for block in blocks:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype in ("rows", "cols"):
                walk_blocks(block.get("blocks") or [])
                continue
            key = block.get("key")
            if key:
                parts.append(_text_from_block(str(btype or ""), data.get(key)))

    blocks = layout.get("blocks")
    if isinstance(blocks, list):
        walk_blocks(blocks)
    text = "\n".join(p for p in parts if p)
    return len(text)

def build_generation_meta(
    report: dict[str, Any],
    *,
    started_at: datetime | str | None = None,
    duration_sec: float | None = None,
    llm_usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    completed_at = datetime.now(timezone.utc)
    text_chars = count_report_text_characters(report)
    meta: dict[str, Any] = {
        "started_at": _iso_dt(started_at),
        "completed_at": completed_at.isoformat(),
        "duration_sec": round(duration_sec, 2) if duration_sec is not None else None,
        "characters": {
            "text": text_chars,
        },
    }
    if llm_usage:
        meta["tokens"] = llm_usage
        if llm_usage.get("cost_usd") is not None:
            meta["cost_usd"] = llm_usage["cost_usd"]
    return meta


def build_pipeline_meta(
    *,
    started_at: datetime | str | None = None,
    duration_sec: float | None = None,
    llm_usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Report artifact 없이 파이프라인 LLM usage·시간만 기록."""
    completed_at = datetime.now(timezone.utc)
    meta: dict[str, Any] = {
        "started_at": _iso_dt(started_at),
        "completed_at": completed_at.isoformat(),
        "duration_sec": round(duration_sec, 2) if duration_sec is not None else None,
    }
    if llm_usage:
        meta["tokens"] = llm_usage
        if llm_usage.get("cost_usd") is not None:
            meta["cost_usd"] = llm_usage["cost_usd"]
    return meta

def attach_generation_meta(
    report: dict[str, Any],
    *,
    started_at: datetime | str | None = None,
    duration_sec: float | None = None,
    llm_usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = dict(report)
    out["generation"] = build_generation_meta(
        report,
        started_at=started_at,
        duration_sec=duration_sec,
        llm_usage=llm_usage,
    )
    out["generation"]["characters"]["json_file"] = len(
        json.dumps(out, ensure_ascii=False)
    )
    return out
