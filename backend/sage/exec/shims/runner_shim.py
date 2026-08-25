"""run_task worker shim — progress·path setup (LLM import chain 없음)."""

from __future__ import annotations

import sys

import cfg
from sage.logg import error, info

TASK_ROOT = cfg.root_path / "nodes" / "report" / "task"


def safe_report(reporter, message: str, state: str = "running") -> None:
    if reporter and hasattr(reporter, "update"):
        try:
            reporter.update(message, state=state)
            return
        except Exception:
            pass
    if state == "failed":
        error(message)
    elif state == "completed":
        info(message)
    else:
        info(message)


def setup_task_paths() -> None:
    root = cfg.root_path
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(TASK_ROOT) not in sys.path:
        sys.path.insert(0, str(TASK_ROOT))
