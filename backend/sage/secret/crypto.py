"""Secret key 암·복호화."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


def normalize_key_name(key_name: str) -> str:
    return key_name.strip().upper()


def _encryption_raw() -> str:
    """SecretKey DB 암·복호화 전용 — SAGE_API_KEY(FE REST 인증)와 분리."""
    for name in ("SAGE_SECRET_ENCRYPTION_KEY", "SAGE_MASTER_KEY"):
        raw = (os.environ.get(name) or "").strip()
        if raw:
            return raw
    return "sage-dev-change-me"


def _fernet() -> Fernet:
    digest = hashlib.sha256(_encryption_raw().encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_api_key(plain: str) -> str:
    if not plain:
        raise ValueError("api_key 는 비어 있을 수 없습니다.")
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_api_key(cipher: str) -> str:
    if not cipher:
        raise ValueError("암호화된 api_key 가 비어 있습니다.")
    try:
        return _fernet().decrypt(cipher.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError(
            "api_key 복호화에 실패했습니다. SAGE_SECRET_ENCRYPTION_KEY 를 확인하세요."
        ) from e
