"""Shared-secret API key auth for the SAGE HTTP API."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Request

import cfg
from sage.logg import info, warning

API_KEY_HEADER = "API-Key"
AUTH_QUERY_PARAM = "api_key"


def auth_enabled() -> bool:
    """True when ``SAGE_API_AUTH_ENABLED`` is on and ``SAGE_API_KEY`` is set."""
    return cfg.sage_api_auth_enabled and bool(cfg.sage_api_key)


def announce_auth_mode() -> None:
    if auth_enabled():
        info("API auth enabled (header: API-Key, query: api_key for SSE)")
    elif cfg.sage_api_auth_enabled and not cfg.sage_api_key:
        warning(
            "SAGE_API_AUTH_ENABLED is on but SAGE_API_KEY is unset — auth disabled. "
            "Set SAGE_API_KEY or turn off SAGE_API_AUTH_ENABLED."
        )
    else:
        info(
            "API auth disabled (SAGE_API_AUTH_ENABLED=off). "
            "Set SAGE_API_AUTH_ENABLED=on and SAGE_API_KEY for protected mode."
        )


def _extract_api_key(request: Request) -> str | None:
    header_key = request.headers.get(API_KEY_HEADER)
    if header_key:
        return header_key.strip()

    # /admin/* JWT uses Authorization: Bearer — do not treat as API key
    if not request.url.path.startswith("/admin/"):
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()

    query_key = request.query_params.get(AUTH_QUERY_PARAM)
    if query_key:
        return query_key.strip()

    return None


def _is_public_path(request: Request) -> bool:
    """Health + OpenAPI UI only — API routes stay protected."""
    if request.method != "GET":
        return False
    path = request.url.path
    if path in {"/", "/openapi.json", "/redoc"}:
        return True
    return path == "/docs" or path.startswith("/docs/")


def _is_admin_path(request: Request) -> bool:
    """Admin UI uses JWT (cookie/Bearer) — separate from SAGE_API_KEY."""
    return request.url.path.startswith("/admin/")


async def verify_api_key(request: Request) -> None:
    """FastAPI dependency — enforces ``SAGE_API_KEY`` when configured."""
    if not auth_enabled() or _is_public_path(request) or _is_admin_path(request):
        return

    provided = _extract_api_key(request)
    expected = cfg.sage_api_key
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
