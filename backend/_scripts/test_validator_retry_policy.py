#!/usr/bin/env python3
"""Validator llm_retry — contract 위반은 같은 generate 에서 LLM 재생성."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.report.validators import TaskExecutorPatternsValidator, validate_codegen_output


def main() -> int:
    errors: list[str] = []
    v = TaskExecutorPatternsValidator()
    if not getattr(v, "llm_retry", True):
        errors.append("TaskExecutorPatternsValidator.llm_retry should be True")
    wrap = SimpleNamespace(
        code=(
            "async def run_task(task, ctx, reporter=None):\n"
            "    ctx.update_task(task.task_id, key='x', value={})\n"
            '    _ = df.to_dict(orient="records")\n'
            "    ctx.save()\n"
        )
    )
    try:
        v.validate(wrap)
        errors.append("to_dict(records) should fail validation")
    except ValueError:
        pass

    async def check_codegen() -> None:
        code = (
            "async def run_task(task, ctx, reporter=None):\n"
            "    ctx.update_task(task.task_id, key='x', value={})\n"
            '    df.to_dict(orient="records")\n'
            "    ctx.save()\n"
        )
        try:
            await validate_codegen_output(
                code,
                task_type="narrative",
                plan_id="pl-x",
                data_id="did-x",
                rid="rp-x",
                context=[],
                tools=[],
            )
            errors.append("validate_codegen_output should reject to_dict(records)")
        except ValueError:
            pass
        except Exception as exc:
            errors.append(f"unexpected: {type(exc).__name__}: {exc}")

    asyncio.run(check_codegen())

    if errors:
        for e in errors:
            print(f"FAIL {e}", file=sys.stderr)
        return 1
    print("OK validator retry policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
