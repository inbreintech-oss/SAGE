"""Verify data-load executor refresh — run: py -3 scripts/verify_stock_load.py"""
import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reports" / "rp-5ef35932" / "srcs" / "task-load-and-update-stock-data-a1b2c3d4.py"
DID_ADAPTER = ROOT / "data" / "did-stock-volume-price-48323ae5" / "pangea" / "v1"


async def main() -> None:
    sys.path.insert(0, str(DID_ADAPTER))
    spec = importlib.util.spec_from_file_location("task_load", SRC)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    from sage.data.pangea import PangeaExDataFrame
    from sage.models.node import TaskRun
    from sage.report.context import TaskContext

    did = "did-stock-volume-price-48323ae5"
    pgdf = PangeaExDataFrame(did=did)
    df_before = pgdf.to_pandas("PangeaSchema")
    vol_before = int(df_before["volume"].sum()) if "volume" in df_before.columns else -1

    task = TaskRun(
        task_id="task-load-verify",
        plan_id="pl-verify",
        data_id=did,
        title="verify",
        description="verify",
        instruction="verify",
        type="data",
    )
    ctx = TaskContext(plan_id="pl-verify", rid="rp-verify")
    await mod.run_task(task, ctx, reporter=None)

    board = ctx.catalog().get(task.task_id, {})
    keys = list((board.get("keys") or {}).keys())
    primary_key = keys[0] if keys else None
    rows = ctx.get_result(task.task_id, primary_key) if primary_key else []
    meta = ctx.get_result(task.task_id, "dataset_meta") or {}
    if not meta and len(keys) > 1:
        for k in keys[1:]:
            v = ctx.get_result(task.task_id, k)
            if isinstance(v, dict) and v:
                meta = v
                break
    vol_after = int(meta.get("total_volume", 0))
    top = rows[0] if isinstance(rows, list) and rows else (rows if isinstance(rows, dict) else {})

    print(f"parquet_volume_sum_before={vol_before}")
    print(f"context_total_volume={vol_after}")
    print(f"top_ticker={top.get('stock_code')} volume={top.get('accumulated_volume')} price={top.get('current_price')}")


if __name__ == "__main__":
    asyncio.run(main())
