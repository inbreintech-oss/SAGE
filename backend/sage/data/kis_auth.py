"""한국투자증권 OpenAPI 인증 헬퍼 — APP_KEY/SECRET 조회와 access token 발급.

생성된 MCP 도구가 ``KIS_BASE_URL`` 과 토큰을 공유한다.
키 값은 소스에 두지 않고 SecretKey(``secret_id`` / provider=kis) 또는 환경변수로 읽는다.
"""
import asyncio
import json
import os
from datetime import datetime, timedelta

import httpx

from sage.mcp import call

KIS_TOKEN_TOOL = "tm-kis-token-e8a7b6c5"
KIS_TOKEN_CACHE_FILE = os.path.expanduser("~/.kis_token_cache.json")
KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"


async def get_kis_app_credentials(*, tool_path: str | None = None) -> tuple[str | None, str | None]:
    """도구 정보의 secret_id → SecretKey.keys[] 에서 APP_KEY / APP_SECRET 조회.

    tool_path 생략 시 SecretKey provider=kis 로 보조 조회한다.
    """
    app_key = None
    app_secret = None
    try:
        from sage.secret import get_secret, resolve_tool_secret_id

        secret_id = None
        if tool_path:
            try:
                secret_id = await resolve_tool_secret_id(tool_path)
            except Exception:
                secret_id = None
        if secret_id:
            app_key, app_secret = await asyncio.wait_for(
                asyncio.gather(
                    get_secret("APP_KEY", secret_id=secret_id),
                    get_secret("APP_SECRET", secret_id=secret_id),
                ),
                timeout=8.0,
            )
        else:
            app_key, app_secret = await asyncio.wait_for(
                asyncio.gather(
                    get_secret("APP_KEY", provider="kis"),
                    get_secret("APP_SECRET", provider="kis"),
                ),
                timeout=8.0,
            )
    except Exception:
        app_key = os.environ.get("KIS_APPKEY") or os.environ.get("APP_KEY")
        app_secret = os.environ.get("KIS_APPSECRET") or os.environ.get("APP_SECRET")
    return app_key, app_secret


def _parse_cache_expiry(cached: dict) -> datetime | None:
    for key in ("access_token_token_expired", "expired_at"):
        raw = cached.get(key)
        if not raw:
            continue
        try:
            return datetime.strptime(str(raw), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


def _load_cached_kis_token() -> str | None:
    if not os.path.exists(KIS_TOKEN_CACHE_FILE):
        return None
    try:
        with open(KIS_TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
            cached = json.load(f)
        expired_at = _parse_cache_expiry(cached)
        if expired_at and expired_at > datetime.now() + timedelta(minutes=5):
            return cached.get("access_token")
    except Exception:
        return None
    return None


async def _issue_kis_access_token(app_key: str, app_secret: str) -> str | None:
    url = f"{KIS_BASE_URL}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload, headers={"content-type": "application/json"})
        if response.status_code != 200:
            return None
        data = response.json()
    token = data.get("access_token")
    if not token:
        return None
    try:
        os.makedirs(os.path.dirname(KIS_TOKEN_CACHE_FILE), exist_ok=True)
        with open(KIS_TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return token


async def get_kis_access_token(*, tool_path: str | None = None) -> str | None:
    cached = _load_cached_kis_token()
    if cached:
        return cached

    try:
        token_res = await asyncio.wait_for(
            call(
                KIS_TOKEN_TOOL,
                "get_kis_access_token",
                {"request": {"force_refresh": False}},
            ),
            timeout=10.0,
        )
        access_token = token_res.get("access_token")
        if access_token:
            return access_token
    except Exception:
        pass

    cached = _load_cached_kis_token()
    if cached:
        return cached

    app_key, app_secret = await get_kis_app_credentials(tool_path=tool_path)
    if app_key and app_secret:
        return await _issue_kis_access_token(app_key, app_secret)
    return None
