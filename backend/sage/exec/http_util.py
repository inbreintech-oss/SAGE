"""Async HTTP helpers (stdlib — extra deps 없음)."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any


def _request(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    timeout_sec: float = 30.0,
) -> tuple[int, dict[str, Any] | str]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = resp.getcode()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        code = exc.code
    try:
        return code, json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return code, raw


async def request_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    timeout_sec: float = 30.0,
) -> tuple[int, dict[str, Any] | str]:
    return await asyncio.to_thread(
        _request, method, url, body=body, timeout_sec=timeout_sec
    )
