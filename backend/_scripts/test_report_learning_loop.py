#!/usr/bin/env python3
"""report/generate 자가학습·재시도 검증 — retrying 이벤트 카운트."""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from urllib.request import Request, urlopen

API = "http://localhost:8090/report/generate"
PAYLOAD = {
    "did": "did-fx-report-1bab8d81",
    "query": "환율 동향 분석",
}


def run_once(timeout_sec: int = 900) -> dict:
    body = json.dumps(PAYLOAD).encode("utf-8")
    req = Request(
        API,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    retries: list[dict] = []
    events: list[str] = []
    rid = ""
    failed = False
    completed = False
    t0 = time.time()

    with urlopen(req, timeout=timeout_sec) as resp:
        buf = ""
        while True:
            if time.time() - t0 > timeout_sec:
                break
            chunk = resp.read(4096)
            if not chunk:
                break
            buf += chunk.decode("utf-8", errors="replace").replace("\r\n", "\n")
            while "\n\n" in buf:
                part, buf = buf.split("\n\n", 1)
                event_name = ""
                data_line = ""
                for ln in part.splitlines():
                    if ln.startswith("event:"):
                        event_name = ln[6:].strip()
                    elif ln.startswith("data:"):
                        data_line = ln[5:].strip()
                if not data_line:
                    continue
                try:
                    ev = json.loads(data_line)
                except json.JSONDecodeError:
                    continue
                if event_name:
                    ev["event"] = event_name
                name = ev.get("event", "")
                events.append(name)
                if name == "retrying":
                    retries.append(ev)
                if name == "failed":
                    failed = True
                if name == "completed":
                    completed = True
                if ev.get("rid"):
                    rid = ev["rid"]
                if not event_name and ev.get("msg"):
                    if "재시도" in ev["msg"] or "retry" in ev["msg"].lower():
                        event_name = "retrying"

    by_task: dict[str, int] = defaultdict(int)
    by_phase: dict[str, int] = defaultdict(int)
    for r in retries:
        key = r.get("task_id") or r.get("msg", "?")[:40]
        by_task[key] += 1
        by_phase[r.get("phase") or "?"] += 1

    return {
        "rid": rid,
        "retry_count": len(retries),
        "retries": retries,
        "by_task": dict(by_task),
        "by_phase": dict(by_phase),
        "failed": failed,
        "completed": completed,
        "elapsed_sec": round(time.time() - t0, 1),
    }


def main() -> int:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"POST {API}")
    print(f"payload={PAYLOAD}")
    prev_retries = None
    for i in range(1, runs + 1):
        print(f"\n=== run {i}/{runs} ===")
        try:
            result = run_once()
        except Exception as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"rid={result['rid']} elapsed={result['elapsed_sec']}s")
        print(f"retry_count={result['retry_count']} failed={result['failed']} completed={result['completed']}")
        print(f"by_phase={result['by_phase']}")
        print(f"by_task={result['by_task']}")
        for r in result["retries"]:
            print(f"  - [{r.get('phase')}] {r.get('msg', '')[:100]}")
        if prev_retries is not None and result["retry_count"] < prev_retries:
            print(f"IMPROVED: retries {prev_retries} -> {result['retry_count']}")
        prev_retries = result["retry_count"]
        if result["retry_count"] == 0 and result["completed"] and not result["failed"]:
            print("OK: no retries")
            return 0
    if prev_retries == 0:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
