"""LLM 호출 토큰 사용량 — 보고서 파이프라인 단위 집계 (contextvars).

동시 ``/report/generate`` 요청마다 asyncio Task ContextVar 가 분리됩니다.
LLM ``generate_async`` 는 ``contextvars.copy_context()`` 로 worker thread 에 동일
컨텍스트를 전달 — 전역 fallback 없음.
"""

from __future__ import annotations

import json
import threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from sage.llm.pricing import estimate_cost_usd, rate_label


@dataclass
class LLMUsageStats:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0
    cost_usd: float = 0.0
    by_model: dict[str, dict[str, Any]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def add(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        inp = max(0, int(input_tokens or 0))
        out = max(0, int(output_tokens or 0))
        cost = max(0.0, float(cost_usd or 0.0))
        with self._lock:
            self.calls += 1
            self.input_tokens += inp
            self.output_tokens += out
            self.total_tokens += inp + out
            self.cost_usd += cost
            bucket = self.by_model.setdefault(
                model,
                {"input": 0, "output": 0, "total": 0, "calls": 0, "cost_usd": 0.0},
            )
            bucket["input"] += inp
            bucket["output"] += out
            bucket["total"] += inp + out
            bucket["calls"] += 1
            bucket["cost_usd"] = round(bucket.get("cost_usd", 0.0) + cost, 8)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "total": self.total_tokens,
                "calls": self.calls,
                "cost_usd": round(self.cost_usd, 6),
                "by_model": dict(self.by_model),
            }


_usage_ctx: ContextVar[LLMUsageStats | None] = ContextVar("llm_usage", default=None)


def current_usage() -> LLMUsageStats | None:
    return _usage_ctx.get()


def begin_report_generation() -> LLMUsageStats:
    """현재 asyncio Task(=요청)에 usage 집계 객체를 바인딩."""
    stats = LLMUsageStats()
    _usage_ctx.set(stats)
    return stats


def reset_report_generation() -> None:
    """요청 종료 시 현재 Task 컨텍스트만 해제 (다른 요청에 영향 없음)."""
    _usage_ctx.set(None)


def record_llm_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    *,
    provider: str | None = None,
    call_site: str | None = None,
    estimated: bool = False,
) -> None:
    """Aggregate usage for the current report; per-call detail → report.log only."""
    inp = max(0, int(input_tokens or 0))
    out = max(0, int(output_tokens or 0))
    cost = estimate_cost_usd(model, inp, out)

    stats = _usage_ctx.get()
    if stats is not None:
        stats.add(model, inp, out, cost)

    from sage.logg import append_report_log

    label = provider or "llm"
    est_tag = " est" if estimated else ""
    msg = (
        f"[llm{est_tag}] {label}/{model} in={inp} out={out} total={inp + out} "
        f"cost=${cost:.6f}"
    )
    if stats is not None:
        snap = stats.to_dict()
        msg += f" report_total=${snap['cost_usd']:.6f} calls={snap['calls']}"
    if call_site:
        msg += f" site={call_site}"
    append_report_log(msg)


def _usage_dict(stats: LLMUsageStats | dict[str, Any] | None) -> dict[str, Any]:
    if stats is None:
        return {}
    return stats.to_dict() if isinstance(stats, LLMUsageStats) else dict(stats or {})


def format_usage_brief(stats: LLMUsageStats | dict[str, Any] | None) -> str:
    """한 줄 요약 — completed SSE·콘솔 1회용.

    ``in`` = API prompt_token_count 합 (instruction + user + llm_attach + schema 등 전부 과금).
    ``out`` = completion/candidates 토큰 합.
    """
    data = _usage_dict(stats)
    if not data:
        return ""
    inp = int(data.get("input", 0) or 0)
    out = int(data.get("output", 0) or 0)
    cost = float(data.get("cost_usd", 0) or 0)
    calls = int(data.get("calls", 0) or 0)
    by_model: dict[str, Any] = data.get("by_model") or {}

    if calls == 0:
        return "LLM usage 집계 없음 (usage_metadata 미수신)"

    total = inp + out
    if int(data.get("total", 0) or 0) != total:
        total = int(data.get("total", 0) or 0)

    if len(by_model) == 1:
        model = next(iter(by_model))
        rate_hint = f"{model} {rate_label(model)}"
    elif by_model:
        rate_hint = f"{len(by_model)} models (호출별 단가 합산)"
    else:
        rate_hint = "model unknown"

    return (
        f"LLM {calls} calls · prompt_in={inp:,} gen_out={out:,} "
        f"tokens={total:,} cost=${cost:.4f} [{rate_hint}] "
        f"(in=prompt+attach billed)"
    )


def persist_report_usage_log(
    rid: str,
    stats: LLMUsageStats | dict[str, Any] | None = None,
) -> None:
    """report.log / usage.json 용 — 콘솔 출력 없음."""
    data = _usage_dict(stats or current_usage())
    if not data or int(data.get("calls", 0) or 0) == 0:
        return
    from sage.logg import append_report_log

    append_report_log(f"LLM usage rid={rid}: {json.dumps(data, ensure_ascii=False)}")


def log_report_usage_summary(
    rid: str,
    stats: LLMUsageStats | dict[str, Any] | None = None,
    *,
    phase: str = "completed",
) -> str:
    """Deprecated console helper — file only; brief 는 format_usage_brief 사용."""
    persist_report_usage_log(rid, stats)
    return format_usage_brief(stats)
