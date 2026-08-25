"""release 태스크 — upstream patch API (codegen 참고, import 작성 금지).

조회·재실행 시 srcs/*.py 만 실행. QA 수정은 apply_upstream_patches 로 upstream 에 반영.
**전체 모듈 triple-quote embed 금지** — syntax 오류·재발 방지.
"""

# narrative_tid = task.context[i]   # 하드코딩 금지
# visual_tid = task.context[j]      # chart/table executor 수정 시만
#
# # 1) draft QA → ctx.update_task(narrative_tid, key="report_document", ...)
# # 2) finalize_report_document → ctx.update_task(..., key="report", ...)
# # 3) release_summary
#
# # 4) upstream srcs — llm_attach upstream_sources 의 snippet 으로 old/new patch
# apply_upstream_patches(ctx.rid, {
#     narrative_tid: [],   # 필수 — 변경 없어도 re-save
#     # visual_tid: [{"old": "exact snippet from upstream_sources", "new": "patched snippet"}],
# })
#
# read_task_body(ctx.rid, narrative_tid)  # 디스크 body 참고 (실행 시 patch API 가 read)
