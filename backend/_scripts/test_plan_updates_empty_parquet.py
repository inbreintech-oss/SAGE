#!/usr/bin/env python3
"""plan_updates: 0행 parquet + FAIL dump 는 재조회 대상."""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.data.dump_store import (  # noqa: E402
    dump_dir,
    list_dump_keys_for_model,
    plan_updates_from_dumps,
)

MODEL = "PangeaSchema"
TARGET = {
    "model": MODEL,
    "keys": ["stock_code", "trade_date"],
    "fields": [
        "stock_code",
        "trade_date",
        "stock_name",
        "sector_large",
        "foreign_net_buy",
        "institution_net_buy",
    ],
}
TOOLS = {
    "kis/investor": {"fields": ["foreign_net_buy", "institution_net_buy"]},
    "kis/stock-info": {"fields": ["stock_name", "sector_large"]},
}
FIELDS = ["stock_name", "sector_large", "foreign_net_buy", "institution_net_buy"]
SOURCES = [
    {"type": "tool", "tool_path": "kis/investor"},
    {"type": "tool", "tool_path": "kis/stock-info"},
]


def _write_response(root: Path, tool: str, key: str, status: str) -> None:
    slug = tool.replace("/", "-")
    path = dump_dir(root) / MODEL / slug / key / "response.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "tool_path": tool,
                "model": MODEL,
                "key": key,
                "created_at_ms": int(time.time() * 1000),
                "response": {"status": status, "items": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _plan(root: Path, keys: list):
    return plan_updates_from_dumps(
        root,
        model=MODEL,
        target=TARGET,
        metadata_tools=TOOLS,
        metadata_field_ttl={"_default_ttl": 1, "stock_name": {"ttl": 30}},
        sources=SOURCES,
        req_keys=keys,
        req_fields=FIELDS,
        known_models=[MODEL],
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_response(root, "kis/investor", "005930", "FAIL")
        _write_response(root, "kis/stock-info", "005930", "FAIL")
        _write_response(root, "kis/investor", "000660", "FAIL")

        boot = list_dump_keys_for_model(root, model=MODEL, meta_keys=TARGET["keys"])
        if sorted(boot) != ["000660", "005930"]:
            raise SystemExit(f"dump keys bootstrap failed: {boot}")

        if _plan(root, []) != []:
            raise SystemExit("empty req_keys must still short-circuit")

        fail_plan = _plan(root, ["005930", "000660"])
        if not fail_plan:
            raise SystemExit("FAIL dumps must not count as fresh")
        planned_keys = sorted({k for item in fail_plan for k in item["keys"]})
        if planned_keys != ["000660", "005930"]:
            raise SystemExit(f"FAIL plan keys mismatch: {fail_plan}")

        _write_response(root, "kis/investor", "005930", "SUCCESS")
        _write_response(root, "kis/stock-info", "005930", "SUCCESS")
        mixed = _plan(root, ["005930", "000660"])
        covered = {
            field
            for item in mixed
            if "005930" in item["keys"]
            for field in item["fields"]
        }
        if "foreign_net_buy" in covered or "stock_name" in covered:
            raise SystemExit(f"SUCCESS dump still marked 005930 stale: {mixed}")
        leftover = {k for item in mixed for k in item["keys"]}
        if leftover != {"000660"}:
            raise SystemExit(f"expected only 000660 remaining, got {mixed}")

        tuple_plan = _plan(root, [("005930", "2026-08-21"), ("000660", "2026-08-21")])
        tuple_stale = {item["keys"][0][0] for item in tuple_plan if item["keys"]}
        if "005930" in tuple_stale:
            raise SystemExit(f"composite keys did not match ticker SUCCESS dump: {tuple_plan}")
        if "000660" not in tuple_stale:
            raise SystemExit(f"composite keys missed FAIL ticker: {tuple_plan}")

    print("OK plan_updates empty-parquet / FAIL-dump")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
