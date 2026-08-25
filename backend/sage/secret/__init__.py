"""SecretKey 조회 — 생성된 MCP 도구 code/caller 에서 사용."""

from __future__ import annotations

from typing import Any

from sage.models.doc import SecretKey
from sage.secret.crypto import decrypt_api_key, encrypt_api_key, normalize_key_name


def _decrypt_key_item(key_value: str) -> str:
    return decrypt_api_key(key_value)


def _find_in_record(record: SecretKey | dict[str, Any], key_name: str) -> str | None:
    name = normalize_key_name(key_name)
    keys = record.keys if isinstance(record, SecretKey) else (record.get("keys") or [])
    for item in keys:
        kn = item.key_name if hasattr(item, "key_name") else item.get("key_name")
        kv = item.key_value if hasattr(item, "key_value") else item.get("key_value")
        if kn == name and kv:
            return _decrypt_key_item(kv)
    return None


async def _record_by_provider(user_id: str, provider: str) -> SecretKey | None:
    from sage.db import saged

    wanted = provider.strip().lower()
    if not wanted:
        return None
    exact = await saged.load_secret_by_provider(user_id, provider)
    if exact:
        return exact
    for record in await saged.list_secrets(user_id):
        if (record.provider or "").strip().lower() == wanted:
            return record
    return None


async def resolve_tool_secret_id(tool_path: str) -> str:
    """도구 정보(metadata.json → DB Tool.secret_id)에서 secret_id 를 읽는다."""
    from sage.tool.metadata import read_metadata

    meta = read_metadata(tool_path) or {}
    sid = str(meta.get("secret_id") or "").strip()
    if sid:
        return sid

    from sage.db import saged
    from sage.models import doc

    col = saged.get_collection(doc.Tool)
    raw = await col.find_one({"_id": tool_path}) or await col.find_one({"tool_id": tool_path})
    sid = str((raw or {}).get("secret_id") or "").strip()
    if not sid:
        raise KeyError(f"도구에 secret_id 가 없습니다: {tool_path}")
    return sid


async def get_secret_for_tool(
    key_name: str,
    tool_path: str,
    user_id: str = "admin",
) -> str:
    """도구 정보에 저장된 secret_id 로 SecretKey.keys[] 에서 key_name 을 조회한다."""
    secret_id = await resolve_tool_secret_id(tool_path)
    return await get_secret(key_name, user_id=user_id, secret_id=secret_id)


async def get_secret(
    key_name: str,
    user_id: str = "admin",
    secret_id: str | None = None,
    provider: str | None = None,
) -> str:
    """등록된 SecretKey 를 복호화하여 반환.

    도구 호출은 ``secret_id`` (도구 정보에 저장된 sk-*) 로 해당 문서의 keys[] 만 조회한다.
    ``provider`` 는 secret_id 가 없을 때의 보조 조회이다.
    """
    from sage.db import saged

    name = normalize_key_name(key_name)
    if secret_id:
        record = await saged.load(SecretKey, secret_id)
        if not record:
            raise KeyError(f"SecretKey not found: secret_id={secret_id!r}")
        if record.user_id != user_id:
            raise KeyError(
                f"SecretKey access denied: secret_id={secret_id!r}, user_id={user_id!r}"
            )
        value = _find_in_record(record, name)
        if value is None:
            raise KeyError(
                f"SecretKey not found: secret_id={secret_id!r}, key_name={name!r}"
            )
        return value

    if provider:
        record = await _record_by_provider(user_id, provider)
        if not record:
            raise KeyError(f"SecretKey not found: provider={provider!r}, user_id={user_id!r}")
        value = _find_in_record(record, name)
        if value is None:
            raise KeyError(
                f"SecretKey not found: provider={provider!r}, key_name={name!r}"
            )
        return value

    for record in await saged.list_secrets(user_id):
        value = _find_in_record(record, name)
        if value is not None:
            return value
    raise KeyError(f"SecretKey not found: user_id={user_id!r}, key_name={name!r}")


async def has_secret(
    key_name: str,
    user_id: str = "admin",
    secret_id: str | None = None,
    provider: str | None = None,
) -> bool:
    try:
        await get_secret(key_name, user_id=user_id, secret_id=secret_id, provider=provider)
        return True
    except KeyError:
        return False


async def require_secret(
    key_name: str,
    user_id: str = "admin",
    secret_id: str | None = None,
    provider: str | None = None,
) -> str:
    return await get_secret(key_name, user_id=user_id, secret_id=secret_id, provider=provider)


def get_secret_sync(
    key_name: str,
    user_id: str = "admin",
    secret_id: str | None = None,
) -> str:
    from sage.db import saged

    name = normalize_key_name(key_name)
    if secret_id:
        raw = saged._backend.find_one_sync("secrets", {"_id": secret_id})
        if not raw:
            raise KeyError(f"SecretKey not found: secret_id={secret_id!r}")
        doc_data = saged._read(raw)
        if doc_data.get("user_id") != user_id:
            raise KeyError(
                f"SecretKey access denied: secret_id={secret_id!r}, user_id={user_id!r}"
            )
        value = _find_in_record(doc_data, name)
        if value is None:
            raise KeyError(
                f"SecretKey not found: secret_id={secret_id!r}, key_name={name!r}"
            )
        return value

    doc_data = saged.load_secret_sync(user_id, name)
    if not doc_data:
        raise KeyError(f"SecretKey not found: user_id={user_id!r}, key_name={name!r}")
    value = _find_in_record(doc_data, name)
    if value is None:
        raise KeyError(f"SecretKey not found: user_id={user_id!r}, key_name={name!r}")
    return value


__all__ = [
    "normalize_key_name",
    "encrypt_api_key",
    "decrypt_api_key",
    "get_secret",
    "get_secret_sync",
    "has_secret",
    "require_secret",
    "resolve_tool_secret_id",
    "get_secret_for_tool",
]
