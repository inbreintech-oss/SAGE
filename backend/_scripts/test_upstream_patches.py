#!/usr/bin/env python3
"""Release patch API + validator — triple-quote embed 재발 방지."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.report.task_shell import assemble_task_source
from sage.report.task_sources import save_task_source
from sage.report.upstream_sources import apply_upstream_patches, read_task_body
from sage.report.validators import LlmImportForbiddenValidator, ReleaseTaskValidator

NARRATIVE_BODY = """
async def run_task(task, ctx, reporter=None):
    safe_report(reporter, "[보고서] draft", state="running")
    ctx.update_task(task.task_id, key="report_document", value={})
    ctx.save()
"""

RELEASE_BODY = """
async def run_task(task, ctx, reporter=None):
    narrative_tid = task.context[0]
    draft = ctx.get_result(narrative_tid, "report_document")
    ctx.update_task(narrative_tid, key="report_document", value=draft)
    doc = finalize_report_document(
        draft, plan_id=task.plan_id, did=task.data_id, rid=ctx.rid,
        task_catalog=ctx.catalog(task.context),
    )
    ctx.update_task(task.task_id, key="report", value=doc)
    ctx.update_task(
        task.task_id, key="release_summary",
        value={"overview": "ok", "changes": []},
    )
    apply_upstream_patches(ctx.rid, {narrative_tid: []})
    ctx.save()
"""

BAD_EMBED = """
async def run_task(task, ctx, reporter=None):
    apply_upstream_source_updates(ctx.rid, {"task-x": \"\"\"async def run_task(): pass\"\"\"})
    ctx.save()
"""


def main() -> int:
    errors: list[str] = []

    wrap_ok = SimpleNamespace(code=RELEASE_BODY)
    try:
        LlmImportForbiddenValidator().validate(wrap_ok)
        ReleaseTaskValidator().validate(wrap_ok)
    except Exception as exc:
        errors.append(f"valid release body rejected: {exc}")

    wrap_bad = SimpleNamespace(code=BAD_EMBED)
    try:
        ReleaseTaskValidator().validate(wrap_bad)
        errors.append("embedded apply_upstream_source_updates should fail")
    except ValueError:
        pass

    with tempfile.TemporaryDirectory() as tmp:
        rid = "rp-test-patch"
        tid = "task-narrative-test"
        import sage.report.task_sources as ts

        old_reports = ts.REPORTS_DIR
        ts.REPORTS_DIR = Path(tmp) / "reports"
        try:
            save_task_source(rid, tid, assemble_task_source(NARRATIVE_BODY.strip()))
            body = read_task_body(rid, tid)
            if "report_document" not in body:
                errors.append("read_task_body failed")
            saved = apply_upstream_patches(
                rid,
                {tid: [{"old": "[보고서] draft", "new": "[보고서] final"}]},
                validate="compile",
            )
            if tid not in saved:
                errors.append("apply_upstream_patches did not save")
            patched = read_task_body(rid, tid)
            if "[보고서] final" not in patched:
                errors.append("patch not applied")
        finally:
            ts.REPORTS_DIR = old_reports

    if errors:
        for e in errors:
            print(f"FAIL {e}", file=sys.stderr)
        return 1
    print("OK release upstream patches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
