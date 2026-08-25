# Runtime — type: analyze / visual

## 데이터 접근

| 종류 | API |
|------|-----|
| 통합 원본 | `PangeaExDataFrame(did=task.data_id).to_pandas(model)` |
| 중간 산출물 | `ctx.get_result(task_id, key)` → dict/list |

`task_id`·`key` = `upstream_context` catalog + `llm_attach` — 1회 고정 호출.

## ctx.update_task (visual · analyze 공통)

- 단일: `ctx.update_task(task.task_id, key="...", value=<dict|list>, description="...")`
- 복수 chart/table: `ctx.update_task(task.task_id, chart_a=opt_a, chart_b=opt_b, description="...")`
- 공통 금지(`to_dict(records)` 등) → `runtime_contract` validator-synced 절

공통 금지·update_task 규칙 → `runtime_contract` validator-synced 절.

`llm_attach`: `upstream_payloads`.
