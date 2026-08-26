#!/usr/bin/env python3
"""caller 계약 — kwargs['call'] rewrite / assert / 동일소스 감지."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.tool.caller_contract import (
    assert_caller_mcp_import,
    caller_source_normalized,
    rewrite_kwargs_call_injection,
)
from sage.nodes.lesson_learn import (
    _parse_tool_access_error,
    _validator_fix_hint,
    format_structured_lesson,
    format_retry_feedback,
)

BAD = '''async def main(**kwargs):
    call = kwargs["call"]
    raw = await call(
        "kis/investor",
        "get_investor_trading_flow",
        {"request": {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": "005930"}},
    )
    return raw
'''

GOOD = '''from sage.mcp import call

async def main(**kwargs):
    raw = await call(
        "kis/investor",
        "get_investor_trading_flow",
        {"request": {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": "005930"}},
    )
    return raw
'''


def main() -> int:
    errors: list[str] = []
    try:
        assert_caller_mcp_import(BAD)
        errors.append("assert did not reject kwargs['call']")
    except ValueError as e:
        if "kwargs['call']" not in str(e):
            errors.append(f"assert message weak: {e}")

    try:
        assert_caller_mcp_import(GOOD)
    except Exception as e:
        errors.append(f"assert rejected valid caller: {e}")

    fixed = rewrite_kwargs_call_injection(BAD)
    try:
        assert_caller_mcp_import(fixed)
    except Exception as e:
        errors.append(f"rewrite still invalid: {e}\n{fixed}")
    if "kwargs" in fixed and '["call"]' in fixed:
        errors.append("rewrite left kwargs['call']")
    if caller_source_normalized(fixed) == caller_source_normalized(BAD):
        errors.append("rewrite did not change source")

    access_err = (
        "허용되지 않은 도구 'tm-kis-investor-f765755d' 호출이 감지되었습니다. "
        "현재 사용 가능한 도구 목록은 ['kis/investor'] 입니다."
    )
    bad, allowed = _parse_tool_access_error(access_err)
    if bad != "tm-kis-investor-f765755d" or allowed != ["kis/investor"]:
        errors.append(f"parse tool access: {bad!r} {allowed!r}")
    hint = _validator_fix_hint(access_err)
    if "kis/investor" not in hint or "tm-kis-investor" not in hint:
        errors.append(f"fix hint missing paths: {hint}")
    lesson = format_structured_lesson("ToolAccessValidator", access_err)
    if "kis/investor" not in lesson or "tm-*" not in lesson and "tm-kis" not in lesson:
        errors.append(f"lesson not durable: {lesson}")
    fb = format_retry_feedback("ToolAccessValidator", access_err, attempt=1)
    if "kis/investor" not in fb:
        errors.append(f"retry feedback missing allowed path: {fb}")

    if errors:
        for e in errors:
            print(f"FAIL {e}", file=sys.stderr)
        return 1
    print("OK caller contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
