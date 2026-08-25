"""codegen_contract ↔ validator ↔ runtime enrich 동기 검사."""

from __future__ import annotations

import re

from sage.prompt.report_prompts import load_runtime_contract
from sage.report.codegen_contract import FORBIDDEN_PATTERNS, executor_rules_markdown
from sage.report.validators import TaskExecutorPatternsValidator


def main() -> None:
    md = executor_rules_markdown()
    runtime = load_runtime_contract("data")
    errors: list[str] = []

    for _pat, msg in FORBIDDEN_PATTERNS:
        if msg not in md:
            errors.append(f"executor_rules_markdown missing: {msg}")
        if msg not in runtime:
            errors.append(f"load_runtime_contract missing: {msg}")

    v = TaskExecutorPatternsValidator()
    sample_bad = 'x = df.to_dict(orient="records")'
    try:
        v.validate(type("W", (), {"code": sample_bad})())
        errors.append("validator should reject to_dict(records)")
    except ValueError:
        pass

    if errors:
        raise SystemExit("\n".join(errors))
    print("OK: codegen_contract synced with validator and runtime_contract enrich")


if __name__ == "__main__":
    main()
