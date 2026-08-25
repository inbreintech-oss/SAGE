"""SecretKey secret_id → key_name 목록 해석."""

from __future__ import annotations

import re

from sage.db import saged
from sage.models import doc

_PROVIDER_IN_QUERY = re.compile(
    r"(?:^|\n)\s*provider\s*:\s*([A-Za-z0-9_-]+)\b",
    re.IGNORECASE,
)


def provider_from_query(query: str | None) -> str | None:
    """질의에 `provider: kis` 형태가 있으면 provider 이름을 반환."""
    if not query:
        return None
    m = _PROVIDER_IN_QUERY.search(query)
    if not m:
        return None
    return m.group(1).strip()


async def prepare_tool_secret_fields(
    *,
    user_id: str = "admin",
    secret_id: str | None = None,
    query: str | None = None,
) -> tuple[str | None, str | None, list[str] | None]:
    """ToolGenerateInput 용 (secret_id, provider, keys).

    secret_id 가 없으면 질의의 ``provider:`` 로 SecretKey 를 찾는다.
    생성된 도구 코드는 여전히 secret_id 로만 조회한다 (provider 조회 금지).
    """
    if secret_id and str(secret_id).strip():
        secret_id = str(secret_id).strip()
        record = await saged.load(doc.SecretKey, secret_id)
        if not record:
            raise ValueError(f"SecretKey not found: secret_id={secret_id!r}")
        if record.user_id != user_id:
            raise ValueError(
                f"SecretKey access denied: secret_id={secret_id!r}, user_id={user_id!r}"
            )
        keys = [item.key_name for item in record.keys if item.key_name]
        return secret_id, record.provider, keys or None

    provider = provider_from_query(query)
    if not provider:
        return None, None, None
    record = await saged.load_secret_by_provider(user_id, provider)
    if not record:
        wanted = provider.strip().lower()
        for rec in await saged.list_secrets(user_id):
            if (rec.provider or "").strip().lower() == wanted:
                record = rec
                break
    if not record:
        return None, None, None
    keys = [item.key_name for item in record.keys if item.key_name]
    return record.secret_id, record.provider, keys or None
