# 역할

Plan `type: narrative` — ReportDocument **완성 초안** (`report_document` → `draft.json`). 독자에게 보이는 **단일 보고서**로 조립한다.

[[report/core/composition]] — **role·패턴 순서대로** `layout.blocks`·`data` 조립. `template_id`: `analytical-standard` (도메인 alias `financial-standard`).

[[report/visual_design]] — 섹션 강조·팔레트. `add_block` payload 에 `style` 포함.

[[report/insight_craft]] — 요약·해석·결론. 표+차트만 조립하고 끝내지 말 것. 특정 화면을 복제하지 말 것.

공통 executor 계약: enrich `runtime_contract`. 도메인 Outline·용어는 enrich `domain_brief` (있을 때만).

[[report/report_schema]]

[[report/example/layout_api]]

# 생성 규칙

1. `catalog = ctx.catalog(task.context)` — upstream key 목록 (payload 없음)
2. 칠판 → `ctx.get_result(task.context[i], key)` — **catalog·llm_attach key 그대로**, plan 제목에서 추론 금지
3. `data: dict = {}` 초기화 → `add_block` / `attach_catalog_visuals(ctx, catalog, data, task_ids=task.context)` → chart/table + narrative card
4. **세분화 type** + **`data[key].role`** — [[report/core/composition]] 패턴 `analytical-standard` (chart 직후 `insight_card` + `chart_insight`). 요약(고유명+숫자)·표/차트 해석·결론을 생략하지 말 것. 표 `header`/`columns[].label` 은 **한글**. 차트 payload 의 `grid` 배열을 그대로 두지 말 것. 영문 섹션명(Executive Summary) 강제 금지.
5. `draft = build_report_document(..., layout_blocks=leaves, data=data, tasks=catalog, ...)` — `layout=` 도 blocks 리스트 alias

   ```python
   draft = build_report_document(
       title=...,
       description=...,
       template_id="analytical-standard",
       plan_id=task.plan_id,
       did=task.data_id,
       rid=ctx.rid,
       tasks=catalog,
       layout_blocks=layout_leaves,
       data=data,
   )
   ```

6. 칠판 저장 (둘 중 하나):

   ```python
   ctx.update_task(task.task_id, key="report_document", value=draft, description="...")
   # 또는
   ctx.update_task(task.task_id, report_document=draft, description="...")
   ctx.save()
   ```

7. 섹션·카드 title 에 **task_id·태스크명** 노출 금지
8. **가짜 데이터 금지** — 표 `data`·차트 series 에 숫자/항목명 list literal 을 넣지 말 것. 전부 `ctx.get_result` / attach_catalog_visuals. upstream 이 비면 **빈 표 + 「집계 데이터 없음」** 카드. 데모 업종·예시 수치 **금지**.
9. progress — [[report/reporter_progress]] (`[보고서]` 한글)

# 출력 (JSON Only)

`task_id`, `title`, `description`, `code`
