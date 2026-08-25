"""LLM token cost estimation — env overrides per model prefix."""

from __future__ import annotations

import os

# USD per 1M tokens (input, output) — defaults; override via SAGE_LLM_PRICE_<KEY>_INPUT_MT
_DEFAULT_RATES: dict[str, tuple[float, float]] = {
    "gemini-3.5-flash": (0.075, 0.30),
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-3-flash": (0.075, 0.30),
    "gemini-3.1-pro": (1.25, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "gpt-5": (2.50, 10.00),
    "composer-2.5": (1.25, 6.00),
    "composer-2": (1.25, 6.00),
}

_FALLBACK_INPUT_MT = float(os.environ.get("SAGE_LLM_PRICE_INPUT_MT", "1.0"))
_FALLBACK_OUTPUT_MT = float(os.environ.get("SAGE_LLM_PRICE_OUTPUT_MT", "3.0"))


def _env_rate(model_key: str, direction: str, default_mt: float) -> float:
    env_key = f"SAGE_LLM_PRICE_{model_key.upper().replace('-', '_')}_{direction}_MT"
    raw = os.environ.get(env_key)
    if raw is None:
        return default_mt
    try:
        return float(raw)
    except ValueError:
        return default_mt


def _match_rates(model: str) -> tuple[float, float]:
    name = (model or "").strip().lower()
    for prefix, rates in sorted(_DEFAULT_RATES.items(), key=lambda x: -len(x[0])):
        if name.startswith(prefix) or prefix in name:
            inp_mt = _env_rate(prefix, "INPUT", rates[0])
            out_mt = _env_rate(prefix, "OUTPUT", rates[1])
            return inp_mt, out_mt
    return _FALLBACK_INPUT_MT, _FALLBACK_OUTPUT_MT


def match_rates(model: str) -> tuple[float, float]:
    return _match_rates(model)


def rate_label(model: str) -> str:
    inp_mt, out_mt = _match_rates(model)
    return f"${inp_mt:g}/${out_mt:g} per 1M (in/out)"


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    inp_mt, out_mt = _match_rates(model)
    inp = max(0, int(input_tokens or 0))
    out = max(0, int(output_tokens or 0))
    return (inp * inp_mt + out * out_mt) / 1_000_000.0


def estimate_tokens_from_chars(char_count: int) -> int:
    """Heuristic for mixed CJK/Latin prompt size (≈3 chars/token)."""
    return max(0, int(char_count / 3))


def estimate_prompt_input_tokens(
    *,
    prompt_chars: int = 0,
    attach_bytes: int = 0,
) -> int:
    """Pre-call input token guess — text + llm_attach (attach also billed by providers)."""
    return estimate_tokens_from_chars(prompt_chars) + estimate_tokens_from_chars(attach_bytes)
