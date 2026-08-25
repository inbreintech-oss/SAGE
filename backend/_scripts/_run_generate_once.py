#!/usr/bin/env python3
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

payload = {
    "did": "did-stock-data-file-tool-3bf2ad85",
    "query": "코스피 분석 및 삼성전자 포함 대표 10종목 선정",
    "tools": ["kis/stock"],
}
headers = {"API-Key": os.environ.get("SAGE_API_KEY", "").strip()}
url = "http://127.0.0.1:8090/report/generate"

print("POST", url)
print("payload=", json.dumps(payload, ensure_ascii=False))
started = time.time()
last_event = ""
rid = ""

with httpx.Client(timeout=httpx.Timeout(30.0, read=900.0)) as client:
    with client.stream("POST", url, json=payload, headers=headers) as resp:
        print("HTTP", resp.status_code)
        if resp.status_code != 200:
            print(resp.read().decode()[:2000])
            sys.exit(1)
        for line in resp.iter_lines():
            if time.time() - started > 900:
                print("[TIMEOUT]")
                sys.exit(2)
            if line.startswith("event:"):
                last_event = line.split(":", 1)[1].strip()
                continue
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(ev, dict) or "msg" not in ev:
                continue
            event = last_event or ev.get("event", "")
            msg = ev.get("msg", "")
            rid = ev.get("rid") or rid
            print(f"[{time.strftime('%H:%M:%S')}] [{event}] {msg}")
            if event == "failed":
                err = ev.get("error", "")
                if err:
                    print(err[:6000])
                sys.exit(1)
            if event == "completed":
                print(f"OK rid={rid} elapsed={time.time() - started:.1f}s")
                sys.exit(0)

print("stream ended without completed", last_event, rid)
sys.exit(1)
