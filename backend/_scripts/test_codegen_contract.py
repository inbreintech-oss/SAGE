#!/usr/bin/env python3
"""Codegen contract guard — prelude(import 금지) vs validator 모순 재발 방지."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.report.task_shell import prelude_symbols
from sage.report.validators import (
    DataTaskFlowValidator,
    JsonLiteralInPythonValidator,
    LlmImportForbiddenValidator,
    ReleaseTaskValidator,
)

_NARRATIVE_REQUIRED_PRELUDE = ("add_block", "layout_block", "attach_catalog_visuals", "build_report_document")
_RELEASE_REQUIRED_PRELUDE = ("apply_upstream_patches", "read_task_body", "finalize_report_document")

# LLM body 에 import 를 *요구*하면 안 되는 패턴 (prelude era)
_FORBIDDEN_VALIDATOR_SNIPPETS = (
    r"raise ValueError\([^)]*import\s+필수",
    r"`from sage\.mcp import call`\s*import\s+필수",
)

MCP_BODY = '''
async def run_task(task, ctx, reporter=None):
    pgdf = PangeaExDataFrame(did=task.data_id)
    _ = pgdf.to_pandas("PangeaSchema")
    plan = pgdf.plan_updates("PangeaSchema", keys=["005930"])
    for item in plan:
        for ticker in item["keys"]:
            row = await call("kis/stock", "get_stock_item_detail", {"itcode": ticker})
            pgdf.queue_update("PangeaSchema", [row], tool_path="kis/stock")
    pgdf.apply_pending_updates("PangeaSchema")
    ctx.update_task(task.task_id, key="stock_list", value=[], description="x")
    ctx.save()
'''


def _check_validator_source() -> list[str]:
    text = (ROOT / "sage/report/validators.py").read_text(encoding="utf-8")
    enrich = (ROOT / "sage/prompt/enrich.py").read_text(encoding="utf-8")
    errors: list[str] = []
    for pat in _FORBIDDEN_VALIDATOR_SNIPPETS:
        if re.search(pat, text):
            errors.append(f"validators.py contains forbidden pattern: {pat!r}")
    if "import: from sage.mcp import call" in enrich:
        errors.append("enrich.py still tells LLM to import call")
    if "prelude 주입" not in enrich or "import 작성 금지" not in enrich:
        errors.append("report tools_spec lost prelude no-import contract")
    if "kwargs['call']" not in enrich:
        errors.append("non-report tools_spec must forbid kwargs['call']")
    if "from sage.mcp import call" not in enrich:
        errors.append("non-report tools_spec must require from sage.mcp import call")
    return errors


def _check_prelude_body_acceptance() -> list[str]:
    errors: list[str] = []
    wrap = SimpleNamespace(code=MCP_BODY)
    try:
        LlmImportForbiddenValidator().validate(wrap)
    except Exception as exc:
        errors.append(f"LlmImportForbidden rejected valid body: {exc}")
    v = DataTaskFlowValidator()
    v.requires_mcp = True
    v.allowed_models = {"PangeaSchema"}
    try:
        v.validate(wrap)
    except Exception as exc:
        errors.append(f"DataTaskFlow rejected valid body: {exc}")
    if "call" not in prelude_symbols():
        errors.append("prelude missing call symbol")
    syms = set(prelude_symbols())
    for name in _NARRATIVE_REQUIRED_PRELUDE:
        if name not in syms:
            errors.append(f"prelude missing {name} (narrative instruction requires it)")
    for name in _RELEASE_REQUIRED_PRELUDE:
        if name not in syms:
            errors.append(f"prelude missing {name} (release instruction requires it)")
    bad = SimpleNamespace(code='async def run_task(task, ctx, reporter=None):\n    x = {"show": true}\n    ctx.save()\n')
    try:
        JsonLiteralInPythonValidator().validate(bad)
        errors.append("JsonLiteralInPythonValidator did not reject true")
    except ValueError:
        pass
    bad_embed = SimpleNamespace(
        code='async def run_task(task, ctx, reporter=None):\n'
        '    apply_upstream_source_updates(ctx.rid, {"task-x": """broken""")\n'
        "    ctx.save()\n"
    )
    try:
        ReleaseTaskValidator().validate(bad_embed)
        errors.append("ReleaseTaskValidator should reject apply_upstream_source_updates embed")
    except ValueError:
        pass
    tofu_body = (
        "async def run_task(task, ctx, reporter=None):\n"
        "    narrative_tid = task.context[0]\n"
        "    draft = ctx.get_result(narrative_tid, \"report_document\")\n"
        "    ctx.update_task(narrative_tid, key=\"report_document\", value=draft)\n"
        "    doc = finalize_report_document(\n"
        "        draft, plan_id=task.plan_id, did=task.data_id, rid=ctx.rid,\n"
        "        task_catalog=ctx.catalog(task.context),\n"
        "    )\n"
        "    ctx.update_task(task.task_id, key=\"report\", value=doc)\n"
        "    ctx.update_task(\n"
        "        task.task_id, key=\"release_summary\",\n"
        f"        value={{'overview': '{chr(0x2006) * 20}', 'changes': []}},\n"
        "    )\n"
        "    apply_upstream_patches(ctx.rid, {narrative_tid: []})\n"
        "    ctx.save()\n"
    )
    try:
        ReleaseTaskValidator().validate(SimpleNamespace(code=tofu_body))
        errors.append("ReleaseTaskValidator should reject unicode-space Hangul tofu")
    except ValueError:
        pass
    from sage.report.quality import lint_report_document

    tofu_doc = {
        "layout": {"type": "rows", "blocks": [{"type": "summary_card", "key": "s"}]},
        "data": {"s": {"role": "executive_summary", "content": "\u2006" * 24}},
    }
    lint = lint_report_document(tofu_doc)
    if not any(i.get("code") == "hangul_stripped" for i in lint.get("issues") or []):
        errors.append("lint_report_document missed hangul_stripped")
    if lint.get("passed"):
        errors.append("hangul_stripped report should not pass quality lint")
    return errors


def main() -> int:
    errors = _check_validator_source() + _check_prelude_body_acceptance()
    if errors:
        for e in errors:
            print(f"FAIL {e}", file=sys.stderr)
        return 1
    print("OK codegen contract (prelude vs validators)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
