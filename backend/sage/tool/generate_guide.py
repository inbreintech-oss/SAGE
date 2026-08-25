"""tool/generate 질의에서 코드로 복사할 상수만 뽑는다.

TR_ID·URL 경로처럼 질의에 적힌 리터럴을 codegen 선가이드로 붙인다.
인증·HTTP 골격은 ``sage.secret.prompt`` / tool_pack 예시가 담당한다.
"""

from __future__ import annotations

import re

_TR_ID = re.compile(
    r"(?:TR[_\s-]?ID)\s*[:=]\s*[`'\"]?([A-Z][A-Z0-9_]+)[`'\"]?",
    re.IGNORECASE,
)
_URL_PATH = re.compile(
    r"(?:URL\s*경로|url\s*path|API\s*경로)\s*[:=]\s*[`'\"]?(/[^\s`'\"]+)[`'\"]?",
    re.IGNORECASE,
)
_FULL_URL = re.compile(r"https?://[^\s`'\"]+", re.IGNORECASE)


def extract_query_literals(query: str | None) -> dict[str, str]:
    """질의에서 코드에 그대로 넣을 TR_ID / URL 을 뽑는다."""
    if not query:
        return {}
    out: dict[str, str] = {}
    m = _TR_ID.search(query)
    if m:
        out["tr_id"] = m.group(1).strip()
    m = _URL_PATH.search(query)
    if m:
        out["url_path"] = m.group(1).strip().rstrip(".,;")
    m = _FULL_URL.search(query)
    if m:
        out["full_url"] = m.group(0).strip().rstrip(".,;")
    return out


def build_tool_codegen_guide(query: str | None) -> str:
    """질의 리터럴만. 인증·HTTP 골격은 secret 블록 / tool_pack 예시를 따른다."""
    lit = extract_query_literals(query)
    if not lit:
        return ""
    lines = ["## 코드에 그대로 넣을 상수 (철자 변경 금지)", "```python"]
    if lit.get("tr_id"):
        lines.append(f'TR_ID = "{lit["tr_id"]}"')
    if lit.get("url_path"):
        lines.append(f'API_PATH = "{lit["url_path"]}"')
    if lit.get("full_url"):
        lines.append(f'BASE_URL = "{lit["full_url"]}"')
    lines.append("```")
    return "\n".join(lines)
