"""Pangeaze docker_pool exec smoke — stocks10.csv unify."""
from __future__ import annotations

import json
import sys

import httpx

import cfg

PAYLOAD = {
    "category": "finance",
    "description": "파일 데이터만 사용, 도구는 사용 안함",
    "name": "증권 데이터 파일데이터 도구x",
    "query": "주식 목록 파일로 통합 스키마 생성",
    "sources": [
        {
            "format": "csv",
            "options": {"encoding": "utf-8"},
            "path": "uploaded/stocks10.csv",
            "sheets": [
                {
                    "columns": [
                        {"name": "srtnCd", "selected": True, "type": "str"},
                        {"name": "itmsNm", "selected": True, "type": "str"},
                        {"name": "mrktCtg", "selected": False, "type": "str"},
                        {"name": "clpr", "selected": True, "type": "float"},
                    ],
                    "name": "Sheet1",
                }
            ],
            "type": "file",
        }
    ],
}


def _parse_sse_chunk(chunk: str) -> tuple[str, dict] | None:
    event = ""
    data: dict = {}
    for line in chunk.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            raw = line[5:].strip()
            if raw:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"msg": raw}
    if not event and not data:
        return None
    return event, data


def main() -> int:
    headers = {}
    if cfg.sage_api_key:
        headers["API-Key"] = cfg.sage_api_key
    print("POST /data/pangeaze ...")
    completed = False
    did = None
    with httpx.Client(timeout=600.0, headers=headers) as client:
        with client.stream("POST", "http://localhost:8090/data/pangeaze", json=PAYLOAD) as resp:
            resp.raise_for_status()
            buffer = ""
            for text in resp.iter_text():
                buffer += text.replace("\r\n", "\n")
                while "\n\n" in buffer:
                    chunk, buffer = buffer.split("\n\n", 1)
                    parsed = _parse_sse_chunk(chunk)
                    if not parsed:
                        continue
                    event, data = parsed
                    msg = data.get("msg", data)
                    if not event:
                        if data.get("did") and data.get("schema"):
                            event = "completed"
                        elif "실패" in str(msg):
                            event = "error"
                    print(f"[{event}] {msg}")
                    if event == "completed":
                        completed = True
                        did = data.get("did")
                    if event == "error":
                        print("FAILED", data, file=sys.stderr)
                        return 1
    if not completed:
        print("FAILED — no completed event", file=sys.stderr)
        return 1
    print("SUCCESS did=", did)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
