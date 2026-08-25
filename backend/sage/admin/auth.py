"""JWT auth for /admin/* routes."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from authlib.jose import jwt
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from sage.admin.passwords import jwt_secret
from sage.admin.repository import AdminRepository
from sage.db import SAGEDataStore, get_db
from sage.models.admin import AdminUser


COOKIE_NAME = "sage_admin_token"
TOKEN_TTL_HOURS = int(os.environ.get("SAGE_ADMIN_TOKEN_TTL_HOURS", "12"))


class TokenPayload(BaseModel):
    sub: str
    login_id: str
    role: str


def create_access_token(user: AdminUser) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.user_id,
        "login_id": user.login_id,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=TOKEN_TTL_HOURS)).timestamp()),
    }
    return jwt.encode({"alg": "HS256"}, payload, jwt_secret()).decode("utf-8")


def decode_access_token(token: str) -> TokenPayload:
    try:
        data = jwt.decode(token, jwt_secret())
        claims = dict(data)
        return TokenPayload(sub=claims["sub"], login_id=claims["login_id"], role=claims["role"])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    cookie = request.cookies.get(COOKIE_NAME)
    return cookie or None


async def get_current_user(
    request: Request,
    db: SAGEDataStore = Depends(get_db),
) -> AdminUser:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_access_token(token)
    repo = AdminRepository(db)
    user = await repo.get_user(payload.sub)
    if not user or user.disabled:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    return user


OptionalAdminUser = Annotated[AdminUser | None, Depends(get_current_user)]
