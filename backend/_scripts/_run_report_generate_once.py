#!/usr/bin/env python3
"""One-shot POST /report/generate SSE."""
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
    p.add_argument("--did", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--tools", nargs="*", default=[])
    args = p.parse_args()

    payload = {"did": args.did, "query": args.query, "tools": list(args.tools)}
    headers = {"API-Key": cfg.sage_api_key, "Accept": "text/event-stream"}
    url = f"http://127.0.0.1:{cfg.port}/report/generate"
    print("POST", url)
    print("payload", json.dumps(payload, ensure_ascii=False))

    rid = None
    with httpx.Client(timeout=httpx.Timeout(30.0, read=3600.0)) as client:
        with client.stream("POST", url, json=payload, headers=headers) as resp:
            print("HTTP", resp.status_code)
            if resp.status_code != 200:
                print(resp.read().decode(errors="replace"))
                return 1
            cur = None
            buf = ""
            for chunk in resp.iter_text():
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.rstrip("\r")
                    if line.startswith("event:"):
                        cur = line[6:].strip()
                    elif line.startswith("data:"):
                        raw = line[5:].strip()
                        if not raw:
                            continue
                        try:
                            obj = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        rid = obj.get("rid") or rid
                        msg = obj.get("msg", "")
                        print(f"[{cur}] {msg[:220]}")
                        if cur == "completed":
                            print("SUCCESS rid=", rid)
                            return 0
                        if cur == "failed":
                            print(json.dumps(obj, ensure_ascii=False, indent=2)[:3000])
                            return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
