#!/usr/bin/env python3
"""계약 위반 본문이 compress·MaxRetriesExceeded 메시지에 남아야 한다."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import ValidationError

from sage.errs import MaxRetriesExceededError
from sage.models.node import PangeaOutput
from sage.nodes.lesson_learn import compress_error_for_lesson, format_retry_feedback

BAD_SHRINK = '''
async def unify_data(did, reporter=None):
    FILE_SOURCE_IDS: list[str] = []
    SELECTED_TICKERS = ["005930", "000660", "005380", "035420", "051910",
        "000270", "005490", "068270", "207940", "105560"]
    res = await call("kis/stock", "get_stock_item_detail", {"itcode": SELECTED_TICKERS[0]})
    raise RuntimeError("x")
'''


def main() -> int:
    try:
        PangeaOutput(
            metadata={},
            schema_code="class PangeaSchema: ...",
            adapter="class A: ...",
            unify_logic_code=BAD_SHRINK,
        )
    except ValidationError as exc:
        raw = str(exc)
    else:
        raise SystemExit("BAD_SHRINK should fail PangeaOutput validation")

    core = compress_error_for_lesson(raw)
    if "15개" not in core and "축소" not in core:
        raise SystemExit(f"compress dropped contract bullets:\n{core!r}\n--- raw ---\n{raw[:800]}")
    if "import asyncio" in core or "SELECTED_TICKERS = [" in core:
        raise SystemExit(f"compress leaked unify source:\n{core[:400]!r}")

    fb = format_retry_feedback("PydanticValidator", raw)
    if "15개" not in fb and "축소" not in fb:
        raise SystemExit(f"retry feedback dropped bullets:\n{fb}")

    err = MaxRetriesExceededError(3, last_error=fb)
    if "동일 contract 위반" in str(err) and "15개" not in str(err) and "축소" not in str(err):
        raise SystemExit(f"MaxRetriesExceeded hid the cause:\n{err}")
    if "15개" not in str(err) and "축소" not in str(err) and "계약 위반" not in str(err):
        raise SystemExit(f"MaxRetriesExceeded missing cause:\n{err}")

    print("OK compress_contract_error")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
