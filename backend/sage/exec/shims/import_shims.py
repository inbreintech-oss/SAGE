"""Exec worker import shims — ``sage.report.runner`` → ``task_runtime``."""

from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from typing import Any, Iterator

from sage.exec import task_runtime

_SHIM_RUNNER = "sage.report.runner"


def _snapshot_module(name: str) -> Any | None:
    return sys.modules.get(name)


def _restore_module(name: str, previous: Any | None) -> None:
    if previous is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = previous


def _build_runner_shim() -> types.ModuleType:
    mod = types.ModuleType(_SHIM_RUNNER)
    mod.safe_report = task_runtime.safe_report
    mod.task_source_path = task_runtime.task_source_path
    mod.apply_upstream_source_updates = task_runtime.apply_upstream_source_updates
    mod.apply_upstream_patches = task_runtime.apply_upstream_patches
    mod.read_task_body = task_runtime.read_task_body
    return mod


@contextmanager
def exec_import_shims() -> Iterator[None]:
    """report / unify / tool exec 직전 — runner import 가 LLM chain 을 타지 않게."""
    prev_runner = _snapshot_module(_SHIM_RUNNER)
    sys.modules[_SHIM_RUNNER] = _build_runner_shim()
    try:
        yield
    finally:
        _restore_module(_SHIM_RUNNER, prev_runner)
