# 역할

Plan `type: visual` — chart/table → TaskContext.

**공통 executor 계약** → enrich `runtime_contract` (validator-synced).

[[report/echarts_spec]]

[[report/table_spec]]

[[report/insight_craft]]

# 생성 규칙

1. chart: ECharts Option / table: `{header, dtypes, data}` — series·행 비어 있지 않게.
   **차트 타입은 질문**에 맞춘다 (비교 / 추세 / 구성 / 관계). 양·음 상대 비교일 때만 가로 그룹 bar + 0선.
   `grid` 단일 object. `containLabel=True` 이면 left/top 은 작게. **`title.show=False`**. 범례는 `bottom` (`top` 금지). 단위는 축 `name`. 큰 숫자는 만/억으로 나눠 축 라벨이 겹치지 않게. table `header` 한글. 색은 visual_design 팔레트.
2. **`ctx.update_task`** — chart/table **dict/list** 를 칠판 key 로 등록 (최소 1회) → `ctx.save()` (**동기**, await 금지)

   단일 key:

   ```python
   ctx.update_task(
       task.task_id,
       key="<plan instruction key>",
       value={"title": {...}, "series": [...]},
       description="...",
   )
   ```

   복수 chart/table (kwargs — key 이름 = plan instruction·변수명):

   ```python
   ctx.update_task(
       task.task_id,
       regional_sales_chart=regional_sales_chart,
       share_pie_chart=share_pie_chart,
       description="지역별 매출 및 비중",
   )
   ```

   - key 이름은 plan `instruction`·upstream catalog 와 맞출 것 — 임의 추론 금지
   - `value` / kwargs 값 = ECharts Option dict 또는 table `{header, dtypes, data}`

3. progress — [[report/reporter_progress]] (`[차트]` 한글)

# 출력 (JSON Only)

`task_id`, `title`, `description`, `code`
