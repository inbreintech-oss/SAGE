"""Report block type · data.role registry (3안: type 세분화 + data.role)."""

from __future__ import annotations

from typing import Any

# --- 세분화 type (권장) ---
SEMANTIC_BLOCK_TYPES = frozenset({
    "document_title",
    "section_title",
    "summary_card",
    "insight_card",
    "kpi_card",
    "text_card",
    "closing_card",
    "metrics_table",
    "appendix_table",
    "primary_chart",
    "secondary_chart",
    "rows",
    "cols",
})

LEGACY_BLOCK_TYPES = frozenset({"header", "card", "echart", "chart", "table"})

CONTAINER_TYPES = frozenset({"rows", "cols"})

KNOWN_ROLES = frozenset({
    "report_title",
    "section_header",
    "executive_summary",
    "kpi_row",
    "key_findings",
    "chart_insight",
    "table_insight",
    "conclusions",
    "methodology",
    "metrics_table",
    "appendix_table",
    "primary_chart",
    "secondary_chart",
})

DATA_STYLE_KEYS = frozenset({"variant", "accent", "density", "border"})
DATA_STYLE_VARIANTS = frozenset({"default", "emphasis", "muted", "highlight", "callout"})
DATA_STYLE_DENSITIES = frozenset({"compact", "normal", "spacious"})

TYPE_DEFAULT_ROLE: dict[str, str] = {
    "document_title": "report_title",
    "section_title": "section_header",
    "summary_card": "executive_summary",
    "insight_card": "chart_insight",
    "kpi_card": "kpi_row",
    "text_card": "methodology",
    "closing_card": "conclusions",
    "metrics_table": "metrics_table",
    "appendix_table": "appendix_table",
    "primary_chart": "primary_chart",
    "secondary_chart": "secondary_chart",
    "header": "report_title",
    "card": "key_findings",
    "echart": "primary_chart",
    "chart": "primary_chart",
    "table": "metrics_table",
}

TYPE_ALLOWED_ROLES: dict[str, frozenset[str]] = {
    "document_title": frozenset({"report_title"}),
    "section_title": frozenset({"section_header"}),
    "summary_card": frozenset({"executive_summary"}),
    "insight_card": frozenset({"chart_insight", "table_insight", "key_findings"}),
    "kpi_card": frozenset({"kpi_row", "executive_summary"}),
    "text_card": frozenset({"methodology", "key_findings"}),
    "closing_card": frozenset({"conclusions"}),
    "metrics_table": frozenset({"metrics_table"}),
    "appendix_table": frozenset({"appendix_table"}),
    "primary_chart": frozenset({"primary_chart"}),
    "secondary_chart": frozenset({"secondary_chart"}),
    "header": frozenset({"report_title", "section_header"}),
    "card": frozenset({
        "executive_summary", "kpi_row", "key_findings",
        "chart_insight", "table_insight", "conclusions", "methodology",
    }),
    "echart": frozenset({"primary_chart", "secondary_chart"}),
    "chart": frozenset({"primary_chart", "secondary_chart"}),
    "table": frozenset({"metrics_table", "appendix_table"}),
}

PATTERN_REQUIRED_ROLES = frozenset({
    "report_title",
    "executive_summary",
    "metrics_table",
    "table_insight",
    "primary_chart",
    "chart_insight",
    "conclusions",
})

_SUMMARY_ROLES = frozenset({"executive_summary", "kpi_row"})
_CARD_TYPES = frozenset({
    "card", "summary_card", "insight_card", "kpi_card", "text_card", "closing_card",
})


def is_known_role(role: str | None) -> bool:
    return bool(role and role in KNOWN_ROLES)


def payload_role(payload: Any) -> str | None:
    if isinstance(payload, dict):
        role = payload.get("role")
        if isinstance(role, str) and role.strip():
            return role.strip()
    return None


def resolve_role(
    payload: Any,
    block_type: str,
    *,
    layout_role: str | None = None,
) -> str | None:
    """data.role 우선, layout.role(legacy) 차순, type 기본값."""
    role = payload_role(payload)
    if is_known_role(role):
        return role
    if is_known_role(layout_role):
        return layout_role
    default = TYPE_DEFAULT_ROLE.get(block_type)
    return default if is_known_role(default) else None


def role_allowed_for_type(block_type: str, role: str | None) -> bool:
    if not role:
        return True
    allowed = TYPE_ALLOWED_ROLES.get(block_type)
    if allowed is None:
        return is_known_role(role)
    return role in allowed


def chart_block_type(index: int) -> tuple[str, str]:
    """(layout type, data.role) — 1-based chart index."""
    if index <= 1:
        return "primary_chart", "primary_chart"
    return "secondary_chart", "secondary_chart"


def table_block_type(index: int, key: str = "") -> tuple[str, str]:
    blob = key.lower()
    if index > 1 or "appendix" in blob or "detail" in blob:
        return "appendix_table", "appendix_table"
    return "metrics_table", "metrics_table"


def ensure_payload_role(entry: Any, role: str | None) -> Any:
    if role and isinstance(entry, dict) and "role" not in entry:
        patched = dict(entry)
        patched["role"] = role
        return patched
    return entry


def validate_data_style(style: Any) -> list[str]:
    """data[key].style 검증 — 알 수 없는 키·enum 위반 메시지 목록."""
    if style is None:
        return []
    if not isinstance(style, dict):
        return ["style 은 object 여야 함"]
    issues: list[str] = []
    for key in style:
        if key not in DATA_STYLE_KEYS:
            issues.append(f"알 수 없는 style 키 '{key}'")
    variant = style.get("variant")
    if variant is not None and variant not in DATA_STYLE_VARIANTS:
        issues.append(f"variant '{variant}' 는 허용 enum 아님")
    density = style.get("density")
    if density is not None and density not in DATA_STYLE_DENSITIES:
        issues.append(f"density '{density}' 는 허용 enum 아님")
    accent = style.get("accent")
    if accent is not None and not isinstance(accent, str):
        issues.append("accent 는 string 이어야 함")
    border = style.get("border")
    if border is not None and not isinstance(border, bool):
        issues.append("border 는 boolean 이어야 함")
    return issues
