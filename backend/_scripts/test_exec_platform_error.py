#!/usr/bin/env python3
"""exec platform vs task source error classification."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.report.exec_errors import is_exec_platform_error
from sage.report.runner import is_source_error, ExecPlatformError, TaskSourceError


def main() -> int:
    errors: list[str] = []

    platform_tb = (
        'File "/host/n2/sage/exec/worker_core.py", line 98\n'
        "NameError: name 'source_path' is not defined"
    )
    task_tb = (
        'File "D:/prjs/n2/reports/rp-x/srcs/task-visual.py", line 12\n'
        "KeyError: 'per'"
    )

    if not is_exec_platform_error(platform_tb):
        errors.append("worker_core NameError should be platform")
    if is_exec_platform_error(task_tb):
        errors.append("task KeyError should not be platform")
    if is_source_error(ExecPlatformError("stall")):
        errors.append("ExecPlatformError should not be source_error")
    if not is_source_error(TaskSourceError("KeyError: x")):
        errors.append("task TaskSourceError should be source_error")
    if is_source_error(TaskSourceError(platform_tb)):
        errors.append("platform-wrapped TaskSourceError should not retry")

    if errors:
        for e in errors:
            print("FAIL", e)
        return 1
    print("OK exec platform error policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
