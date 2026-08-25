#!/usr/bin/env python3
"""30분 한도 — report/tool generate 3 cases × 완료까지 반복."""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import httpx
import cfg

DEADLINE_SEC = int(os.environ.get("LOOP_DEADLINE_SEC", "1800"))
PER_CASE_TIMEOUT = int(os.environ.get("LOOP_CASE_TIMEOUT_SEC", "720"))

REPORT_CASES = [
    {
        "name": "report-stock-50",
        "payload": {
            "did": "did-stock-data-file-tool-3bf2ad85",
            "query": "코스피·코스닥 대표 50종목 재무·시장 분석 보고서",
            "tools": ["kis/stock"],
        },
    },
    {
        "name": "report-stock-file",
        "payload": {
            "did": "did-stock-data-file-tool-3bf2ad85",
            "query": "업로드 주식 데이터 기반 섹터별 PER/PBR 요약 보고서",
            "tools": [],
        },
    },
    {
        "name": "report-stock-10",
        "payload": {
            "did": "did-stock-data-file-tool-b09bdfdd",
            "query": "대표 10종목 PER/PBR 스크리닝 및 비교 분석 보고서",
            "tools": ["kis/stock"],
        },
    },
]

TOOL_CASES = [
    {
        "name": "tool-stock-daily",
        "payload": {
            "query": "종목의 일자별 시세확인 도구",
            "tools": ["kis/stock"],
        },
    },
    {
        "name": "tool-stock-detail",
        "payload": {
            "query": "종목 PER PBR 재무지표 조회 도구",
            "tools": ["kis/stock"],
        },
    },
    {
        "name": "tool-fx-rate",
        "payload": {
            "query": "USD KRW 환율 시계열 조회 도구",
            "tools": ["yf/fx-rate"],
        },
    },
]


@dataclass
class CaseResult:
    name: str
    ok: bool
    elapsed: float
    detail: str
    rid_or_tool: str = ""


def _headers() -> dict[str, str]:
    key = os.environ.get("SAGE_API_KEY", "").strip() or cfg.sage_api_key
    return {"API-Key": key, "Accept": "text/event-stream"}


def _parse_sse_message(block: str) -> tuple[str, dict | None]:
    """SSE message block -> (event_name, parsed_data)."""
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


def _consume_sse(
    url: str,
    payload: dict,
    *,
    deadline: float,
    case_timeout: float,
) -> CaseResult:
    started = time.time()
    rid = ""
    err_text = ""

    try:
        with httpx.Client(timeout=httpx.Timeout(30.0, read=case_timeout)) as client:
            with client.stream("POST", url, json=payload, headers=_headers()) as resp:
                if resp.status_code != 200:
                    body = resp.read().decode(errors="replace")[:2000]
                    return CaseResult(
                        "?", False, time.time() - started, f"HTTP {resp.status_code}: {body}"
                    )
                buf = ""
                for chunk in resp.iter_text():
                    if time.time() > deadline:
                        return CaseResult("?", False, time.time() - started, "global deadline")
                    if time.time() - started > case_timeout:
                        return CaseResult("?", False, time.time() - started, "case timeout")
                    buf += chunk.replace("\r\n", "\n")
                    while "\n\n" in buf:
                        block, buf = buf.split("\n\n", 1)
                        event, ev = _parse_sse_message(block)
                        if not ev:
                            continue
                        msg = ev.get("msg", "")
                        rid = ev.get("rid") or ev.get("tool_id") or rid
                        print(f"    [{event}] {str(msg)[:120]}")
                        if event == "failed":
                            err_text = ev.get("error") or msg
                            return CaseResult(
                                "?",
                                False,
                                time.time() - started,
                                str(err_text)[:4000],
                                rid,
                            )
                        if event == "completed":
                            return CaseResult(
                                "?",
                                True,
                                time.time() - started,
                                "completed",
                                rid,
                            )
                if buf.strip():
                    event, ev = _parse_sse_message(buf)
                    if ev:
                        msg = ev.get("msg", "")
                        rid = ev.get("rid") or ev.get("tool_id") or rid
                        if event == "failed":
                            err_text = ev.get("error") or msg
                            return CaseResult(
                                "?",
                                False,
                                time.time() - started,
                                str(err_text)[:4000],
                                rid,
                            )
                        if event == "completed":
                            return CaseResult(
                                "?",
                                True,
                                time.time() - started,
                                "completed",
                                rid,
                            )
    except Exception as exc:
        return CaseResult("?", False, time.time() - started, str(exc)[:2000], rid)

    return CaseResult(
        "?",
        False,
        time.time() - started,
        f"stream ended (rid={rid or 'none'})",
        rid,
    )


def run_report_case(case: dict, deadline: float) -> CaseResult:
    url = f"http://127.0.0.1:{cfg.port}/report/generate"
    print(f"\n>> REPORT {case['name']}")
    print(json.dumps(case["payload"], ensure_ascii=False))
    r = _consume_sse(url, case["payload"], deadline=deadline, case_timeout=PER_CASE_TIMEOUT)
    r.name = case["name"]
    return r


def run_tool_case(case: dict, deadline: float) -> CaseResult:
    url = f"http://127.0.0.1:{cfg.port}/tool/generate"
    print(f"\n>> TOOL {case['name']}")
    print(json.dumps(case["payload"], ensure_ascii=False))
    r = _consume_sse(url, case["payload"], deadline=deadline, case_timeout=PER_CASE_TIMEOUT)
    r.name = case["name"]
    return r


def main() -> int:
    t0 = time.time()
    deadline = t0 + DEADLINE_SEC
    round_no = 0
    summary_path = ROOT / "logs" / "loop_generate_30m.jsonl"

    print(f"loop start deadline={DEADLINE_SEC}s port={cfg.port}")

    while time.time() < deadline:
        round_no += 1
        print(f"\n{'=' * 60}\nROUND {round_no}  elapsed={time.time()-t0:.0f}s\n{'=' * 60}")
        results: list[CaseResult] = []

        for case in REPORT_CASES:
            if time.time() >= deadline:
                break
            results.append(run_report_case(case, deadline))

        for case in TOOL_CASES:
            if time.time() >= deadline:
                break
            results.append(run_tool_case(case, deadline))

        ok_all = all(r.ok for r in results)
        line = {
            "round": round_no,
            "elapsed_sec": round(time.time() - t0, 1),
            "ok_all": ok_all,
            "results": [
                {
                    "name": r.name,
                    "ok": r.ok,
                    "elapsed": round(r.elapsed, 1),
                    "id": r.rid_or_tool,
                    "detail": r.detail[:500],
                }
                for r in results
            ],
        }
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

        print(f"\n--- ROUND {round_no} summary ---")
        for r in results:
            status = "OK" if r.ok else "FAIL"
            print(f"  {status} {r.name} {r.elapsed:.1f}s {r.detail[:80]}")

        if ok_all:
            print(f"\nALL PASS round {round_no} total={time.time()-t0:.1f}s")
            return 0

        if time.time() >= deadline:
            break
        print("\nretrying failed cases next round...")

    print(f"\nDEADLINE reached - not all cases passed ({time.time()-t0:.0f}s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
