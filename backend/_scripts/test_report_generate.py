#!/usr/bin/env python3
"""POST /report/generate E2E smoke — SSE until completed/failed or timeout."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import httpx


def _parse_sse_message(block: str) -> tuple[str, dict | None]:
    event_name = ""
    data_parts: list[str] = []
    for line in block.split("\n"):
        line = line.rstrip("\r")
        if not line or line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data_parts.append(line[5:].lstrip())
    if not data_parts:
        return event_name, None
    raw = "\n".join(data_parts)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return event_name, None
    if not event_name and isinstance(payload, dict):
        event_name = str(payload.get("event") or "")
    return event_name, payload if isinstance(payload, dict) else None


def _headers() -> dict[str, str]:
    key = os.environ.get("SAGE_API_KEY", "").strip()
    if key:
        return {"API-Key": key}
    return {}


def main() -> int:
    payload = {
        "did": os.environ.get("TEST_DID", "did-stock-data-file-tool-3bf2ad85"),
        "query": os.environ.get("TEST_QUERY", "주식 분석"),
    }
    timeout_sec = int(os.environ.get("TEST_TIMEOUT_SEC", "900"))
    url = f"http://{os.environ.get('SAGE_HOST', '127.0.0.1')}:8090/report/generate"

    print(f"POST {url}")
    print(f"payload={json.dumps(payload, ensure_ascii=False)}")
    print(f"timeout={timeout_sec}s\n")

    started = time.time()
    rid = ""
    fail_msgs: list[str] = []

    with httpx.Client(timeout=httpx.Timeout(30.0, read=timeout_sec)) as client:
        with client.stream("POST", url, json=payload, headers=_headers()) as resp:
            if resp.status_code != 200:
                print(f"HTTP {resp.status_code}: {resp.read().decode()[:2000]}")
                return 1
            buf = ""
            for chunk in resp.iter_text():
                if time.time() - started > timeout_sec:
                    print("\n[TIMEOUT]")
                    return 2
                buf += chunk.replace("\r\n", "\n")
                while "\n\n" in buf:
                    block, buf = buf.split("\n\n", 1)
                    event, ev = _parse_sse_message(block)
                    if not ev:
                        continue
                    msg = ev.get("msg", "")
                    rid = ev.get("rid") or rid
                    ts = time.strftime("%H:%M:%S")
                    print(f"[{ts}] [{event}] {msg}")
                    if event == "failed":
                        fail_msgs.append(msg)
                        err = ev.get("error", "")
                        if err:
                            print(err[:4000])
                        return 1
                    if event == "completed":
                        print(f"\nOK rid={rid} elapsed={time.time()-started:.1f}s")
                        return 0
            if buf.strip():
                event, ev = _parse_sse_message(buf)
                if ev:
                    msg = ev.get("msg", "")
                    rid = ev.get("rid") or rid
                    if event == "completed":
                        print(f"\nOK rid={rid} elapsed={time.time()-started:.1f}s")
                        return 0
                    if event == "failed":
                        err = ev.get("error", "")
                        if err:
                            print(err[:4000])
                        return 1

    print(f"\nstream ended without completed rid={rid or 'none'}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
