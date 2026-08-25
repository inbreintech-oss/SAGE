#!/usr/bin/env python3
"""DataTaskFlowValidator — prelude body (no import) smoke."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.report.validators import DataTaskFlowValidator, LlmImportForbiddenValidator

BODY = '''
async def run_task(task, ctx, reporter=None):
    pgdf = PangeaExDataFrame(did=task.data_id)
    df = pgdf.to_pandas("PangeaSchema")
    plan = pgdf.plan_updates("PangeaSchema", keys=["005930"])
    for item in plan:
        for ticker in item["keys"]:
            row = await call("kis/stock", "get_stock_item_detail", {"itcode": ticker})
            pgdf.queue_update("PangeaSchema", [row], tool_path="kis/stock")
    pgdf.apply_pending_updates("PangeaSchema")
    ctx.update_task(task.task_id, key="stock_list", value=[], description="x")
    ctx.save()
'''

def main() -> int:
    wrap = SimpleNamespace(code=BODY)
    LlmImportForbiddenValidator().validate(wrap)
    v = DataTaskFlowValidator()
    v.requires_mcp = True
    v.allowed_models = {"PangeaSchema"}
    v.validate(wrap)
    print("OK call() without import passes validators")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
