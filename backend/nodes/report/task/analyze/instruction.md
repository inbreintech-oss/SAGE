# 역할

Plan `type: analyze` — 선행 태스크 결과 집계·스크리닝.

**공통 executor 계약** → enrich `runtime_contract` (validator-synced).

# 생성 규칙

1. `ctx.get_result(task_id, key)` 또는 `PangeaExDataFrame(...).to_pandas(model)` — catalog key 만
2. 산출: **dict/list** — executor 내 `class X(BaseModel)` 금지. **집계 수치를 소스에 리터럴로 쓰지 말 것** (빈 DF면 빈 summary).
3. **파생 지표가 본 태스크의 산출이다** — 원본 컬럼 합만 저장하면 보고서가 빈약해진다. [[report/insight_craft]]

   질문에 맞게 칠판 value 에 포함 (전부 필수 키가 아님):

   - `universe`: 행·그룹 수, 기간
   - `baseline`: 비교의 기준선 (전체 평균, 전일 등)
   - `rankings`: 그룹명 + 핵심 지표 — **있는 그룹을 숨기지 말 것** (없는 항목을 채워 넣지 말 것)
   - 상위·하위 이름과 수치
   - 두 지표가 엇갈리는 항목 (있을 때만)

   상대 비교가 질문이면 `group_mean - universe_mean`. 시계열·비중·밸류면 그 집계를 한다.

   단일 key:

   ```python
   ctx.update_task(
       task.task_id,
       key="<plan instruction key>",
       value=summary_dict,
       description="...",
   )
   ```

   복수 key (kwargs):

   ```python
   ctx.update_task(
       task.task_id,
       aggregation_summary=summary_dict,
       group_stats=stats_dict,
       description="...",
   )
   ctx.save()
   ```

   - `df.to_dict(orient="records")` / `df.to_dict("records")` **금지** — downstream·llm_attach 로 raw row list 전달 불가
   - 선행 태스크 `llm_attach` row list 를 그대로 `value` 로 복사 금지 — 통계·ranking·summary 로 재가공

4. `ctx.save()` — **동기** (await 금지)
5. progress — [[report/reporter_progress]] (`[분석]` 한글, task_id·key 이름 금지)

# 출력 (JSON Only)

`task_id`, `title`, `description`, `code`
