# Runtime — type: narrative

## 데이터 접근

- `catalog = ctx.catalog(task.context)` — key 메타만
- `ctx.get_result(task.context[i], key)` — catalog·llm_attach key **그대로**

[[report/example/context_api]]
[[report/example/layout_api]]

## 산출

1. `data={}` → `add_block` / `attach_catalog_visuals` → `build_report_document`
2. `ctx.update_task(..., key="report_document", value=draft)` **또는** `report_document=draft`
3. `ctx.save()` — **동기**

`llm_attach`: upstream_payloads — chart/table·집계 실제 key·값 확인.
