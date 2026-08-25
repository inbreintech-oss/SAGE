#!/usr/bin/env python3
"""UpstreamBoardValidator — retry hint, shared lessons, duplicate signature."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.nodes.lesson_learn import (
    format_retry_feedback,
    format_validator_system_priority_block,
)
from sage.nodes.validated_md import load_report_task_shared_lessons


def main() -> int:
    errors: list[str] = []
    err = (
        "get_result key 'selected_stocks_summary' 가 upstream 칠판에 없음. "
        "허용 key: ['market_cap_chart', 'sector_per_chart', 'valuation_analysis_summary'] "
        "— llm_attach upstream_payloads 참고"
    )
    block = format_validator_system_priority_block("UpstreamBoardValidator", err)
    if "최우선" not in block or "selected_stocks_summary" not in block:
        errors.append("system priority block missing bad key")
    if "market_cap_chart" not in block or "valuation_analysis_summary" not in block:
        errors.append("system priority block missing allowed keys")
    if block.find("최우선") > block.find("selected_stocks_summary"):
        errors.append("bad key should appear right after header")

    block2 = format_validator_system_priority_block(
        "TaskExecutorPatternsValidator",
        "raw row json(to_dict records) downstream 전달 금지",
    )
    if "TaskExecutorPatternsValidator" not in block2 or "to_dict records" not in block2:
        errors.append("generic validator should get category + cause in system block")

    fb = format_retry_feedback("UpstreamBoardValidator", err)
    if "selected_stocks_summary" not in fb or "valuation_analysis_summary" not in fb:
        errors.append("retry feedback should name bad key and allowed keys")
    if "plan 제목" not in fb:
        errors.append("retry feedback should warn against inferring keys from plan")

    narrative_dir = ROOT / "nodes" / "report" / "task" / "narrative"
    shared = load_report_task_shared_lessons(
        narrative_dir, frozenset({"UpstreamBoardValidator"})
    )
    if "selected_stocks_summary" not in shared:
        errors.append("narrative should inherit UpstreamBoardValidator lesson from siblings")

    if errors:
        for e in errors:
            print(f"FAIL {e}", file=sys.stderr)
        return 1
    print("OK validator system priority (all validators)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
