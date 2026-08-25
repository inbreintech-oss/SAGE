"""TaskContext — LLM executor 패턴 (prelude 주입, import 금지).

상세 금지 목록은 runtime_contract (validator-synced) 참고.
"""

# --- read ---
# upstream_id = task.context[0]
# summary = ctx.get_result(upstream_id, "aggregation_summary")  # catalog key 그대로

# --- write: 단일 key ---
# ctx.update_task(
#     task.task_id,
#     key="data_summary",
#     value={"count": 50, "regions": ["A", "B"], "total_sales": 1234.5},
#     description="집계 요약",
# )

# --- write: 복수 key (visual chart/table, release report+summary 등) ---
# ctx.update_task(
#     task.task_id,
#     regional_sales_chart=chart_opt,
#     share_pie_chart=pie_opt,
#     description="지역 매출·비중 시각화",
# )

# ctx.save()  # 동기 — await 금지
