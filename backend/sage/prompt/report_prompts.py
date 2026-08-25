"""Report codegen prompt fragments — runtime contract, optional domain brief."""

from __future__ import annotations

from pathlib import Path

import cfg
from sage.prompt.core import resolve_pattern

_PROMPTS_ROOT = Path(cfg.nodes_path) / ".prompts" / "report"
_RUNTIME_DIR = _PROMPTS_ROOT / "runtime"
_BRIEF_DIR = _PROMPTS_ROOT / "brief"

# type → slice stems (under runtime/)
RUNTIME_SLICES: dict[str, tuple[str, ...]] = {
    "data": ("core", "data"),
    "analyze": ("core", "upstream"),
    "visual": ("core", "upstream"),
    "narrative": ("core", "narrative"),
    "release": ("core", "release"),
}

# data.category → brief/*.md stem (없으면 default.md)
BRIEF_CATEGORY_MAP: dict[str, str] = {
    "finance": "finance",
    "stock": "finance",
    "equity": "finance",
}

BRIEF_QUERY_KEYWORDS = (
    "주식",
    "per",
    "pbr",
    "종목",
    "stock",
    "equity",
    "재무",
    "finance",
    "코스피",
    "코스닥",
)


def _read_slice(stem: str) -> str:
    path = _RUNTIME_DIR / f"{stem}.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _finalize_runtime_contract(combined: str, task_type: str | None = None) -> str:
    from sage.report.codegen_contract import executor_rules_markdown
    from sage.report.task_shell import runtime_contract_for_prompt

    shell = runtime_contract_for_prompt()
    rules = executor_rules_markdown().strip()
    body = f"{combined.strip()}\n\n---\n\n{rules}" if combined.strip() else rules
    if (task_type or "").strip() == "release":
        from sage.report.release_contract import release_executor_rules_markdown

        body = f"{body}\n\n---\n\n{release_executor_rules_markdown().strip()}"
    return f"{body}\n\n---\n\n{shell}" if shell.strip() else body


def load_runtime_contract(task_type: str | None = None) -> str:
    """Task type별 runtime slice + validator-synced executor rules."""
    slices = RUNTIME_SLICES.get((task_type or "").strip())
    if not slices:
        slices = RUNTIME_SLICES["data"]
    parts = [block for stem in slices if (block := _read_slice(stem).strip())]
    if not parts:
        legacy = _PROMPTS_ROOT / "runtime.md"
        if legacy.is_file():
            raw = legacy.read_text(encoding="utf-8-sig")
            combined = resolve_pattern(raw, legacy.parent) if "[[" in raw else raw
        else:
            combined = ""
        return _finalize_runtime_contract(combined, task_type)
    combined = "\n\n---\n\n".join(parts)
    if "[[" in combined:
        combined = resolve_pattern(combined, _RUNTIME_DIR)
    return _finalize_runtime_contract(combined, task_type)


def runtime_contract_chars(task_type: str | None = None) -> int:
    return len(load_runtime_contract(task_type))


def _brief_stem_for_category(data_category: str | None) -> str:
    if not data_category or not data_category.strip():
        return "default"
    cat = data_category.strip().lower()
    mapped = BRIEF_CATEGORY_MAP.get(cat, cat)
    if (_BRIEF_DIR / f"{mapped}.md").is_file():
        return mapped
    return "default"


def load_domain_brief(data_category: str | None = None) -> str:
    stem = _brief_stem_for_category(data_category)
    path = _BRIEF_DIR / f"{stem}.md"
    if not path.is_file():
        return ""
    raw = path.read_text(encoding="utf-8-sig")
    if "[[" in raw:
        return resolve_pattern(raw, path.parent)
    return raw


def _text_has_brief_keyword(text: str | None) -> bool:
    if not text or not text.strip():
        return False
    lowered = text.lower()
    return any(k in lowered for k in BRIEF_QUERY_KEYWORDS)


def should_inject_domain_brief(
    *,
    user_description: str | None = None,
    report_query: str | None = None,
    data_category: str | None = None,
) -> bool:
    """narrative 전용 domain brief — 주식 brief 를 모든 description 에 주입하지 않음."""
    if data_category and data_category.strip().lower() in BRIEF_CATEGORY_MAP:
        return True
    if _text_has_brief_keyword(report_query):
        return True
    if _text_has_brief_keyword(user_description):
        return True
    return False
