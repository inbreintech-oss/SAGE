# data — 하드코딩·가짜 데이터 금지



**API 호출 원형·인자**는 `[[report/example/pangea_api]]` 를 따른다. 아래는 비즈니스 규칙만.



## MCP 갱신 (tools 할당 시)



1. `to_pandas(model)` 로 현재 데이터 로드

2. **`plan = pgdf.plan_updates(model, keys=선정목록)`** — dump 폴더 TTL·타임스탬프로 **만료/누락만** 도출. **`keys=` 생략 금지** (0행 parquet 에서 빈 plan → MCP 생략 사고).

   반환 예: `[{"keys": ["id-a", "id-b"], "fields": ["price", "score"]}, ...]`

   - **`item["keys"]`**: `list` (str 또는 tuple) — **dict 아님 → `.get("id")` 금지**

   - **`item["fields"]`**: 갱신 필요 컬럼명 `list[str]`

3. `plan` 이 **빈 list** → 해당 model **MCP call 생략** (parquet 에 행이 있고 dump 가 SUCCESS·TTL 내인 경우만). `to_pandas` 0행이면 빈 plan 을 「최신」으로 해석하지 말 것 — `keys=선정 종목` 을 넘긴다.

4. `plan` 항목별 `for key in item["keys"]:` → `call` → `queue_update` → 마지막에 `apply_pending_updates(model)`

   상세 루프: `[[report/example/pangea_api]]`



**금지:** `for id in selected_ids: await call(...)` 처럼 선정 전체에 무조건 호출 — `plan_updates` 확인 없이 일괄 갱신.

**금지:** `item["keys"].get("id")` / `item["keys"]["id"]` — `keys` 는 list.



## 금지



- `item["keys"].get(...)` / `item["keys"]["..."]` — plan_updates 의 keys 는 **list**

- 분석 대상 **dict/list literals** 로 데이터 채우기 (dataset·MCP 결과만)

- narrative/visual 에서 집계가 비었을 때 **데모 표·예시 순매수** 로 채우기 (`IT/반도체`, `1250000` 등). 빈 결과 + 「데이터 없음」만 허용.

- `call()` 없이 `queue_update()`

- spec 에 없는 MCP `name`·`args`

- metadata [PANGEA TARGETS] 에 없는 model 문자열



## tools 없을 때

`plan_updates` → `call` → `queue_update` 생략. `to_pandas(model)` 로 로드 후 선정·`ctx.update_task`(집계 dict) — `instruction.md` §3 · `runtime_contract` validator-synced.
