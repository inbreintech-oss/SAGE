"""도구 생성 프롬프트용 SecretKey 안내 (값은 포함하지 않음)."""

from __future__ import annotations

from sage.db import saged
from sage.models import doc
from sage.secret.crypto import normalize_key_name


def format_secret_usage_block(
    secret_id: str,
    key_names: list[str],
    provider: str = "",
) -> str:
    """실제 등록 key_name 만 스니펫에 넣는다. 없는 API_TOKEN 을 만들지 말 것."""
    secret_id = (secret_id or "").strip()
    names = [normalize_key_name(k) for k in key_names if k and str(k).strip()]
    if not secret_id or not names:
        return ""

    lines = [
        f"SECRET_ID = \"{secret_id}\"",
        "keys: " + ", ".join(f"`{n}`" for n in names),
        "이 key_name 만 get_secret. 키 값은 소스에 쓰지 말 것.",
    ]
    if provider:
        lines.append(f"provider: `{provider}`")
    return "\n".join(lines)


async def build_secret_prompt(
    secret_id: str | None,
    key_names: list[str] | None,
    *,
    user_id: str = "admin",
) -> str:
    if not secret_id and not key_names:
        return ""

    secret_id = (secret_id or "").strip()
    normalized = [normalize_key_name(k) for k in (key_names or []) if k and str(k).strip()]

    record = None
    if secret_id:
        record = await saged.load(doc.SecretKey, secret_id)
        if record and record.user_id != user_id:
            record = None
        if record and not normalized:
            normalized = [item.key_name for item in record.keys]

    if not secret_id or not normalized:
        return ""

    provider = (record.provider if record else "") or ""
    return format_secret_usage_block(secret_id, normalized, provider)
