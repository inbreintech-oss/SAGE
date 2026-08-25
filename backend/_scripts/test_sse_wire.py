#!/usr/bin/env python3
"""SSE wire format — LoggingRoute + sse_starlette + loop parser."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sse_starlette.event import ensure_bytes

from _scripts.loop_generate_30m import _parse_sse_message


def main() -> int:
    chunk = {
        "event": "completed",
        "data": '{"event":"completed","msg":"ok","tool_id":"tm-x"}',
    }
    wire = ensure_bytes(chunk, "\r\n").decode("utf-8")
    assert "\r\n\r\n" in wire, repr(wire)

    raw_buf = wire
    assert "\n\n" not in raw_buf, "CRLF wire must not contain bare \\n\\n delimiter"

    norm = raw_buf.replace("\r\n", "\n")
    block = norm.split("\n\n")[0]
    event, data = _parse_sse_message(block)
    assert event == "completed", event
    assert data and data.get("tool_id") == "tm-x", data
    print("OK sse wire + parser")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
