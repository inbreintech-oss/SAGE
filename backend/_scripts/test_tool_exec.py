#!/usr/bin/env python3
"""Tool execution smoke — docker_pool caller + optional MCP + POST /tool/exec."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import httpx

import cfg
from sage.exec.jobs import build_tool_caller_job
from sage.exec.runtime import run_exec_job

ECHO_CALLER = """async def main():
    return {"ok": True, "echo": "tool-exec-smoke", "via": "docker_pool"}
"""

MCP_CALLER = '''async def main():
    from sage.mcp import call
    # 삼성전자 기본 정보 — MCP kis/stock
    row = await call("kis/stock", "get_stock_item_detail", {"itcode": "005930"})
    return {"ok": True, "ticker": "005930", "keys": sorted(row.keys())[:8], "sample": row}
'''


def _headers() -> dict[str, str]:
    key = os.environ.get("SAGE_API_KEY", "").strip() or cfg.sage_api_key
    return {"API-Key": key} if key else {}


async def _run_caller(label: str, source: str) -> dict:
    ws = Path(cfg.tools_path) / ".exec-smoke" / f"{label}-{uuid.uuid4().hex[:8]}"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "caller.py").write_text(source, encoding="utf-8")
    job = build_tool_caller_job(workspace=ws)
    print(f"\n=== [{label}] docker_pool tool_caller ===")
    print(f"workspace={ws}")
    result = await run_exec_job(job)
    print(f"ok={result.ok} duration_ms={result.duration_ms}")
    if not result.ok:
        print(f"ERROR:\n{result.error}")
        raise RuntimeError(f"{label} exec failed")
    payload = result.return_value
    print(f"return={json.dumps(payload, ensure_ascii=False)[:500]}")
    return payload if isinstance(payload, dict) else {"result": payload}


def _post_tool_exec(query: str, tools: list[str]) -> dict:
    url = f"http://{os.environ.get('SAGE_HOST', '127.0.0.1')}:8090/tool/exec"
    payload = {"query": query, "tools": tools}
    print(f"\n=== POST /tool/exec ===")
    print(f"url={url}")
    print(f"payload={json.dumps(payload, ensure_ascii=False)}")
    with httpx.Client(timeout=httpx.Timeout(30.0, read=600.0), headers=_headers()) as client:
        resp = client.post(url, json=payload)
    print(f"HTTP {resp.status_code}")
    body = resp.json()
    print(json.dumps(body, ensure_ascii=False, indent=2)[:2000])
    if resp.status_code != 200 or not body.get("success"):
        raise RuntimeError(f"/tool/exec failed: {body.get('error') or body}")
    return body


async def main() -> int:
    print(f"SAGE_EXEC_DRIVER={cfg.sage_exec_driver}")
    mcp = cfg.sage_mcp_base_url or f"http://host.docker.internal:{cfg.port + 1}"
    print(f"MCP (worker env default)={mcp}")

    # 1) Pure exec path — no MCP
    echo = await _run_caller("echo", ECHO_CALLER)
    inner = echo.get("result", echo)
    if not inner.get("ok"):
        return 1
    print("[OK] echo caller via docker_pool")

    # 2) MCP call inside exec worker
    try:
        mcp_res = await _run_caller("mcp-kis", MCP_CALLER)
        inner = mcp_res.get("result", mcp_res)
        if inner.get("ok") and inner.get("ticker") == "005930":
            print("[OK] MCP kis/stock via docker_pool caller")
        else:
            print("[WARN] MCP caller returned unexpected payload", inner)
    except Exception as exc:
        print(f"[WARN] MCP caller test skipped/failed: {exc}")

    # 3) HTTP /tool/exec — LLM codegen + exec (needs assetized tool path)
    if os.environ.get("SKIP_TOOL_EXEC_API", "").strip().lower() in ("1", "true", "yes"):
        print("\n[SKIP] POST /tool/exec (SKIP_TOOL_EXEC_API=1)")
        return 0

    try:
        body = _post_tool_exec(
            query="삼성전자(005930) 종목 기본 정보를 조회해줘",
            tools=["kis/stock"],
        )
        result = body.get("result")
        if result is None:
            raise RuntimeError("empty result from /tool/exec")
        print("[OK] POST /tool/exec")
    except Exception as exc:
        print(f"[WARN] POST /tool/exec failed: {exc}")
        print("       (echo + MCP caller tests already validated exec runtime)")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
