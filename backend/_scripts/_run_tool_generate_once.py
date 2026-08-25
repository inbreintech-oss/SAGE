#!/usr/bin/env python3
"""One-shot POST /tool/generate SSE (docker_pool smoke via validating phase)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
import cfg


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--query", default="종목의 일자별 시세확인 도구")
    p.add_argument("--tools", nargs="*", default=["kis/stock"])
    p.add_argument("--secret-id", default=None)
    args = p.parse_args()

    payload: dict = {"query": args.query, "tools": list(args.tools)}
    if args.secret_id:
        payload["secret_id"] = args.secret_id

    headers = {"API-Key": cfg.sage_api_key, "Accept": "text/event-stream"}
    url = f"http://127.0.0.1:{cfg.port}/tool/generate"
    print("POST", url)
    print("payload", json.dumps(payload, ensure_ascii=False))

    with httpx.Client(timeout=httpx.Timeout(30.0, read=600.0)) as client:
        with client.stream("POST", url, json=payload, headers=headers) as resp:
            print("HTTP", resp.status_code)
            if resp.status_code != 200:
                print(resp.read().decode(errors="replace"))
                return 1
            cur_event = None
            buf = ""
            for chunk in resp.iter_text():
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.rstrip("\r")
                    if line.startswith("event:"):
                        cur_event = line[6:].strip()
                    elif line.startswith("data:"):
                        raw = line[5:].strip()
                        if not raw:
                            continue
                        try:
                            obj = json.loads(raw)
                        except json.JSONDecodeError:
                            print(f"[{cur_event}] (non-json) {raw[:200]}")
                            continue
                        print(f"[{cur_event}] {obj.get('msg', '')[:200]}")
                        if cur_event == "completed":
                            print("tool_id=", obj.get("tool_id"))
                            print(json.dumps(obj.get("result"), ensure_ascii=False, indent=2)[:2000])
                            return 0
                        if cur_event == "failed":
                            print(json.dumps(obj, ensure_ascii=False, indent=2))
                            return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
