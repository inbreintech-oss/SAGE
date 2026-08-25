# PangeaOutput JSON 필드

| 필드 | 타입 | 내용 |
|------|------|------|
| `metadata` | object | `metadata.json` 전체 (sources, targets, tools, fields) |
| `schema_code` | string | `schema.py` **전체** 파이썬 소스 (import·클래스 정의 포함) |
| `adapter` | string | `adapter.py` **전체** 파이썬 소스 |
| `unify_logic_code` | string | `unify.py` **전체** 파이썬 소스 (`unify_data` 함수 필수) |
| `suggested_queries` | string[] | 통합 스키마·소스 기반 **추천 분석 질의 3~5개** (한국어, 구체적) |

## 필수 규칙

1. **5개 필드 모두** 채울 것 — `unify_logic_code` 중간 잘림 금지
2. 코드 문자열은 **완전한 실행 가능 소스** — mock·`pass` only 금지
3. `schema_code` 메인 클래스명은 반드시 `PangeaSchema`
4. 필드 타입 annotation: `str`, `int`, `float`, `bool`, `date`, `datetime` 만 (`string`/`float64` 금지)
5. `metadata.sources[].id` 는 입력 sources 의 `source_id` 와 일치
6. `metadata.targets[].path` 는 `{name}.parquet` 형식

## unify_logic_code — reporter

- `unify_data(did, reporter=None)` 시그니처 필수
- **진행 보고 필수** — [[report/reporter_progress]] (사용자 친화 한글, 내부 API명·model명 금지)
- `reporter.update("메시지", state="running")` — **동기 호출, await 금지**
- **unify 에서 `safe_report` / `except Exception` 금지** — `if reporter: reporter.update(...)` 만
- `await call(...)` 만 async — reporter 와 혼동하지 말 것
- `10% 완료` 단독 메시지 **금지** — `[조회] 종목 정보 (3/100)` 형태 (이름은 파일·질의 선정·도구 응답에서)

## unify_logic_code — 저장

- unify 는 통합 DataFrame 을 **return** — **parquet** 저장은 `handle_pangeaze` 가 수행
- MCP `call` 직후 **TTL 기준선**만 저장:
  - `from sage.data.dump_store import dump_tool_response`
  - `dump_tool_response(did, model, tool_path, key, raw_response)`
- dump 경로: `dump/{model}/{tool_slug}/{key_slug}/response.json`
- `model` = `metadata.targets[].model`, 도구 필드는 metadata `tools`·`fields`(TTL) 와 일치
- `status != SUCCESS` · call 예외 · 0행 → **raise RuntimeError** (빈 DataFrame completed 금지)
- 종목·키 식별자: **파일이 있으면 파일**, **없으면 user_query 종목 수만큼 SELECTED_TICKERS 를 채운다** (10개로 축소 금지). 없는 파일을 get 하지 말 것.

샘플 전체: [[data/example/unify]]
