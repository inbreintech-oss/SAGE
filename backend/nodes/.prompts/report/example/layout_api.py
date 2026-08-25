"""narrative/release — layout API (prelude 주입, import 금지)."""

# catalog = ctx.catalog(task.context)
# data: dict = {}
# leaves = []
# leaves += attach_catalog_visuals(ctx, catalog, data, task_ids=task.context)
# leaves.append(add_block(data, type="summary_card", key="exec_sum", payload={...}, role="executive_summary"))

# draft = build_report_document(
#     title="보고서 제목",
#     description="한 줄 부제",
#     template_id="analytical-standard",
#     plan_id=task.plan_id,
#     did=task.data_id,
#     rid=ctx.rid,
#     tasks=catalog,
#     layout_blocks=leaves,   # layout=leaves 도 동일 (alias)
#     data=data,
# )

# finalize_report_document(
#     draft,
#     task_catalog=catalog,   # tasks= / catalog= 도 동일
#     plan_id=task.plan_id,
#     did=task.data_id,
#     rid=ctx.rid,
#     title=draft.get("title", ""),
#     description=draft.get("description", ""),
# )
