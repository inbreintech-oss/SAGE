# Runtime — type: release



## llm_attach (codegen — QA 참고 전용)



`upstream_payloads` (narrative `report_document` 포함) + `upstream_sources`



**첨부본은 code에 복사하지 않음.** executor는 API로만 patch:



1. draft QA → `ctx.get_result(narrative_tid, "report_document")` dict 수정 → `ctx.update_task`

2. `finalize_report_document` → `update_task` key=`report`

3. `release_summary` → `update_task`

4. `apply_upstream_patches(ctx.rid, {upstream_tid: [ops]})` — narrative `{tid: []}` 필수



`report_qa` 등 자동 QA **금지**.



## upstream 소스 최종본



- `apply_upstream_patches(rid, {task_id: [ops]})` — 디스크 read → old/new snippet patch → save (필수)

- `{task_id: []}` — 변경 없이 re-save (narrative 항상 포함)

- `read_task_body(rid, task_id)` — body 참고

- **`apply_upstream_source_updates` 금지** — `apply_upstream_patches` 만



[[report/example/release_api]]



`upstream_context`: key catalog + QA 안내. patch 규칙은 instruction + quality_rubric enrich/instruction.

