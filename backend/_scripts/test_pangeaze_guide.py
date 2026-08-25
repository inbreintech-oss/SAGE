#!/usr/bin/env python3
"""pangeaze: 생성 전 소스 가이드 + validator 재시도가 금지 구문 대체법을 주는지."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.data.pangeaze_guide import build_pangeaze_user_query, build_unify_codegen_guide
from sage.data.unify_contract import validate_unify_logic_code
from sage.models.node import FileSourceMetadata, ToolSourceMetadata
from sage.nodes.lesson_learn import format_retry_feedback, format_validator_system_priority_block


def main() -> int:
    files = [
        FileSourceMetadata(
            source_id="src-file1",
            path="stocks100.csv",
            columns=["srtnCd", "itmsNm"],
            sample_data=[{"srtnCd": "005930", "itmsNm": "삼성전자"}],
        )
    ]
    tools = [
        ToolSourceMetadata(
            source_id="src-tool1",
            tool_path="kis/investor",
            tool_spec=[{"name": "get_investor_trading_flow", "input": {"properties": {}}}],
        )
    ]
    mixed = build_unify_codegen_guide(files + tools)
    if "src-file1" not in mixed or "FILE_SOURCE_IDS" not in mixed:
        raise SystemExit(f"file+tool guide missing file source_id:\n{mixed}")
    if "SELECTED_TICKERS = []" not in mixed:
        raise SystemExit("file+tool must empty SELECTED_TICKERS")
    if "safe_report" not in mixed or "except Exception" not in mixed:
        raise SystemExit("guide must ban safe_report / except Exception")
    if "kis/investor" not in mixed:
        raise SystemExit("file+tool guide missing tool_path")

    tool_only = build_unify_codegen_guide(tools)
    if "파일 소스 없음" not in tool_only:
        raise SystemExit("tool-only must say no file")
    if "100종" not in tool_only:
        raise SystemExit("tool-only must mention query ticker count")

    q = build_pangeaze_user_query("코스피 100종", files + tools)
    if "작성 가이드" not in q or "src-file1" not in q:
        raise SystemExit("first-attempt user query must include source guide")

    swallow = (
        "Value error, unify_logic_code 계약 위반:\n"
        "- unify.py 에 `except Exception`(또는 BaseException) 이 있다. "
        "reporter 용 try/except·safe_report 도 금지."
    )
    fb = format_retry_feedback("PydanticValidator", swallow, attempt=1)
    if "except Exception" not in fb:
        raise SystemExit(f"retry must name except Exception:\n{fb}")
    if "if reporter" not in fb and "reporter.update" not in fb:
        raise SystemExit(f"retry must give replacement reporter pattern:\n{fb}")
    if "같은 validator" not in fb:
        raise SystemExit(f"retry attempt>=1 must say previous attempt failed same cause:\n{fb}")
    if "동일 contract 위반을 반복하지 말고 전체 executor" in fb:
        raise SystemExit("generic executor-rewrite line must not replace a concrete fix")

    sys_block = format_validator_system_priority_block(
        "PydanticValidator", swallow, attempt=2
    )
    if "0건" not in sys_block and "except Exception" not in sys_block:
        raise SystemExit(f"system retry block must tell how to fix:\n{sys_block}")

    sample = (ROOT / "nodes/.prompts/data/example/unify.py").read_text(encoding="utf-8")
    validate_unify_logic_code(sample)

    reporter_except = '''
async def unify_data(did, reporter=None):
    try:
        if reporter:
            reporter.update("x", state="running")
    except Exception:
        pass
    raise RuntimeError("x")
'''
    try:
        validate_unify_logic_code(reporter_except)
    except ValueError as exc:
        if "except Exception" not in str(exc):
            raise SystemExit(f"reporter except must still fail contract: {exc}")
        if "if reporter" not in str(exc):
            raise SystemExit(f"contract must tell replacement: {exc}")
    else:
        raise SystemExit("reporter except Exception should fail contract")

    print("OK pangeaze_guide")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
