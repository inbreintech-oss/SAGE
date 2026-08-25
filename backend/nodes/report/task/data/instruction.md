# 역할

Plan `type: data` — dataset 로드·MCP 갱신·TaskContext 등록. downstream 의 **신뢰 가능한 원천**.

**공통 executor 금지·TaskContext·progress** → enrich `runtime_contract` (validator-synced, `codegen_contract.py`).

# API · 비즈니스 규칙 (include)

[[report/example/pangea_api]]

[[report/data_anti_hardcode]]

# 생성 규칙 (data 전용)

1. `PangeaExDataFrame(did=task.data_id)` — `dataset_context` [PANGEA TARGETS] model 만

2. plan task `instruction` 대상 행 선정 → model 별:
   - `plan = pgdf.plan_updates(model, keys=selected_...)` — TTL 만료/누락만. **keys 생략 금지**
   - `plan` 빈 list → MCP 생략 (parquet 0행이면 「최신」이 아님 — 선정 keys 로 재조회)
   - `item["keys"]` = **list** (`.get()` 금지), `item["fields"]` = list[str]
   - `call` → `queue_update` → `apply_pending_updates(model)` (model 별 1회)
   - queue_update record 타입 = schema 준수 (int 날짜 YYYYMMDD, date `'YYYY-MM-DD'`)

3. **`ctx.update_task`** — plan instruction key 로 **집계 dict/list** (최소 1회)

   ```python
   ctx.update_task(
       task.task_id,
       key="<plan instruction key>",
       value={"entity_ids": selected_ids, "count": len(selected_ids)},
       description="...",
   )
   ctx.save()
   ```

   - `dataset_context.samples` 는 프로파일 참고 — value 로 복사 금지

4. `safe_report` / `ctx.save()` — **동기** (await 금지)

5. progress — [[report/reporter_progress]] (`[데이터]` `[조회]` 한글만)

# 출력 (JSON Only)

`task_id`, `title`, `description`, `code`
