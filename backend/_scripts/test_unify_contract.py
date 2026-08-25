#!/usr/bin/env python3
"""unify_logic_code 계약 — 빈 DF 성공·파일 강제 거부, 도구만 샘플은 통과."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.data.unify_contract import validate_unify_logic_code

BAD_EMPTY = '''
async def unify_data(did, reporter=None):
    all_records = []
    if not all_records:
        df = pd.DataFrame(columns=["stock_code", "trade_date"])
    if reporter:
        reporter.update("완료", state="completed")
    return {"x": df}
'''

BAD_SWALLOW = '''
async def unify_data(did, reporter=None):
    try:
        res = await call("kis/investor", "get_investor_trading_flow", {})
    except Exception:
        res = {}
    raise RuntimeError("x")
'''

BAD_FILE_REQUIRED = '''
async def unify_data(did, reporter=None):
    try:
        file_df = InMemoryDataBridge.get(did, "src-stock-list")
    except KeyError as exc:
        raise RuntimeError("조회 대상 종목 파일이 없습니다. 파일 소스 또는 질의에 종목코드를 넣으세요.") from exc
    raise RuntimeError("x")
'''

TOOL_ONLY_OK = '''
async def unify_data(did, reporter=None):
    FILE_SOURCE_IDS: list[str] = []
    codes = ["%06d" % i for i in range(100, 120)]
    res = await call("kis/stock", "get_stock_item_detail", {"itcode": codes[0]})
    if not res:
        raise RuntimeError("empty")
    import pandas as pd
    return {"stock_master": pd.DataFrame([{"ticker": codes[0]}])}
'''

BAD_SHRINK = '''
async def unify_data(did, reporter=None):
    FILE_SOURCE_IDS: list[str] = []
    SELECTED_TICKERS = ["005930", "000660", "005380", "035420", "051910",
        "000270", "005490", "068270", "207940", "105560"]
    res = await call("kis/stock", "get_stock_item_detail", {"itcode": SELECTED_TICKERS[0]})
    raise RuntimeError("x")
'''


def main() -> int:
    sample = (ROOT / "nodes/.prompts/data/example/unify.py").read_text(encoding="utf-8")
    validate_unify_logic_code(sample)
    validate_unify_logic_code(TOOL_ONLY_OK)

    try:
        validate_unify_logic_code(BAD_EMPTY)
    except ValueError as exc:
        if "DataFrame(columns" not in str(exc):
            raise SystemExit(f"empty DF not flagged: {exc}")
    else:
        raise SystemExit("empty DF should fail")

    try:
        validate_unify_logic_code(BAD_SWALLOW)
    except ValueError as exc:
        if "except Exception" not in str(exc):
            raise SystemExit(f"swallow not flagged: {exc}")
        if "if reporter" not in str(exc):
            raise SystemExit(f"swallow hint missing replacement: {exc}")
    else:
        raise SystemExit("except Exception swallow should fail")

    try:
        validate_unify_logic_code(BAD_FILE_REQUIRED)
    except ValueError as exc:
        if "파일" not in str(exc):
            raise SystemExit(f"file-required not flagged: {exc}")
    else:
        raise SystemExit("missing-file KeyError path should fail")

    try:
        validate_unify_logic_code(BAD_SHRINK)
    except ValueError as exc:
        if "15개" not in str(exc) and "축소" not in str(exc):
            raise SystemExit(f"shrink-to-10 not flagged: {exc}")
    else:
        raise SystemExit("10-ticker shrink should fail")

    print("OK unify_contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
