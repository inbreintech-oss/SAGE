#!/usr/bin/env python3
"""Smoke test for KIS investor/sector tools.

Uses sage.data.kis_auth when SecretKey DB is available; otherwise falls back to
the existing assetized ``kis/stock`` credentials for local verification only.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

TOOLS = [
    (
        "investor",
        ROOT / "tools/kis/investor/main.py",
        "get_investor_trading_flow",
        "InvestorInquiryRequest",
        {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": "005930"},
        "kis/investor",
    ),
    (
        "sector",
        ROOT / "tools/kis/stock-info/main.py",
        "get_stock_basic_info",
        "StockBasicInfoRequest",
        {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": "005930"},
        "kis/stock-info",
    ),
]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


async def _ensure_kis_credentials() -> None:
    from sage.data import kis_auth

    key, secret = await kis_auth.get_kis_app_credentials(tool_path="kis/investor")
    if key and secret:
        return

    stock_mod = _load_module(ROOT / "tools/kis/stock/main.py", "kis_stock_fallback")
    if getattr(stock_mod, "APP_KEY", None) and getattr(stock_mod, "APP_SECRET", None):
        async def _fallback_credentials(*, tool_path: str | None = None):
            return stock_mod.APP_KEY, stock_mod.APP_SECRET

        kis_auth.get_kis_app_credentials = _fallback_credentials  # type: ignore[method-assign]

    if not await kis_auth.get_kis_access_token(tool_path="kis/investor"):
        token = stock_mod._fetch_token()
        if token:
            async def _fallback_token(*, tool_path: str | None = None):
                return token

            kis_auth.get_kis_access_token = _fallback_token  # type: ignore[method-assign]


async def _run_one(label: str, main_path: Path, fn_name: str, req_cls_name: str, req_kwargs: dict):
    mod = _load_module(main_path, f"kis_tool_{label}")
    fn = getattr(mod, fn_name)
    if hasattr(fn, "fn"):
        fn = fn.fn
    req_cls = getattr(mod, req_cls_name)
    result = await fn(request=req_cls(**req_kwargs))
    payload = result.model_dump() if hasattr(result, "model_dump") else result
    print(f"\n=== [{label}] ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("status") != "SUCCESS":
        raise RuntimeError(f"{label} failed: {payload.get('message')}")
    if label == "investor" and not payload.get("items"):
        raise RuntimeError(f"{label} returned no investor rows")
    if label == "sector" and not payload.get("idx_bztp_mcls_cd_name"):
        raise RuntimeError(f"{label} missing idx_bztp_mcls_cd_name")
    return payload


async def main() -> int:
    await _ensure_kis_credentials()
    for label, path, fn, req_cls, kwargs, _tool_path in TOOLS:
        await _run_one(label, path, fn, req_cls, kwargs)
        print(f"[OK] {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
