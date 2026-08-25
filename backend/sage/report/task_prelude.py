"""Report task executor prelude — import 는 이 파일만 (LLM body 에 import 금지).

exec worker: ``sage.report.runner`` 는 task_runtime shim 으로 해석됨.
심볼 추가/변경은 이 파일만 수정 — 문자열 tuple·regex 주입 테이블 금지.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sage.data.dump_store import dump_tool_response
from sage.data.pangea import PangeaExDataFrame
from sage.mcp import call
from sage.models.node import TaskRun
from sage.report.context import TaskContext
from sage.report.layout import (
    add_block,
    attach_catalog_visuals,
    build_report_document,
    finalize_report_document,
    layout_block,
)
from sage.report.runner import safe_report, task_source_path
from sage.report.upstream_sources import apply_upstream_patches, read_task_body

__all__ = [
    "TaskRun",
    "TaskContext",
    "safe_report",
    "apply_upstream_patches",
    "read_task_body",
    "task_source_path",
    "call",
    "PangeaExDataFrame",
    "dump_tool_response",
    "add_block",
    "layout_block",
    "attach_catalog_visuals",
    "build_report_document",
    "finalize_report_document",
    "pd",
    "np",
]
