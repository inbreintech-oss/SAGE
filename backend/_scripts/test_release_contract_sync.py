#!/usr/bin/env python3
"""release_contract ↔ ReleaseTaskValidator ↔ runtime enrich 동기."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.prompt.report_prompts import load_runtime_contract
from sage.report.release_contract import (
    RELEASE_ATTACH_USAGE,
    RELEASE_CODEGEN_STEPS,
    RELEASE_FORBIDDEN_PATTERNS,
    release_executor_rules_markdown,
)


def main() -> int:
    errors: list[str] = []
    rules = release_executor_rules_markdown()
    runtime = load_runtime_contract("release")

    for _pat, msg in RELEASE_FORBIDDEN_PATTERNS:
        if msg not in rules:
            errors.append(f"release_executor_rules missing: {msg[:60]}")
        if msg not in runtime:
            errors.append(f"load_runtime_contract(release) missing forbidden msg")

    for needle in (
        "apply_upstream_patches(ctx.rid",
        RELEASE_ATTACH_USAGE[:40],
        RELEASE_CODEGEN_STEPS[:40],
        "instruction.md 7번",
    ):
        if needle not in runtime:
            errors.append(f"runtime release missing: {needle[:50]}")

    if errors:
        for e in errors:
            print(f"FAIL {e}", file=sys.stderr)
        return 1
    print("OK release contract synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
