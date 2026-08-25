# DataPangeazer — Pangea 통합 데이터 생성

입력 `sources`·`user_query`를 분석해 **5개 산출물**을 한 번에 생성한다.

| 산출물 | JSON 필드 | 저장 |
|--------|-----------|------|
| 메타데이터 | `metadata` | metadata.json |
| 스키마 | `schema_code` | schema.py |
| 어댑터 | `adapter` | adapter.py |
| 통합 로직 | `unify_logic_code` | unify.py |
| 추천 질의 | `suggested_queries` | 데이터셋 doc (`suggested_queries`) |

[[data/pangea_output]]

[[report/reporter_progress]]

## 작업 순서

1. **sources 분석** — file/tool 각각의 컬럼·출력 구조 파악. **file 은 없어도 된다** (도구만으로 스키마·unify 구성)
2. **metadata 작성** — sources↔targets 매핑, tools·TTL 정의
3. **schema.py** — Pydantic 모델 (메인: `PangeaSchema`, 필요 시 추가 모델)
4. **adapter.py** — 소스별 `transform()` 구현 (도구만이면 도구 어댑터만)
5. **unify.py** — `unify_data(did, reporter)` 로 parquet 초기 구축. 파일 없으면 질의로 종목 목록 생성 후 `call`
6. **suggested_queries** — 통합 스키마 필드·소스를 활용한 **구체적 분석 질의 3~5개** (한국어)

## confirmed_schema (update 전용)

입력이 주어지면 **자유 설계가 아니라** 해당 JSON 스키마 필드·타입을 지켜야 한다.
- `schema.py` / `metadata.targets[].fields` 가 confirmed_schema 와 정합
- `unify_data(did, reporter=None) -> Dict[str, pd.DataFrame]` 계약은 create 와 **동일** (df_map 인자 금지)

## suggested_queries

- `PangeaSchema` 및 targets 필드명을 반영한 **실행 가능한** 질의
- 예: `"PER·PBR 과 시가총액으로 스크리닝"`, `"업종별 기관·외국인 순매수 비교"`
- 모호한 질문·스키마에 없는 필드 언급 금지

## metadata

[[data/pangea_metadata]]

- `sources[].id` = 입력 `source_id` 와 동일
- `sources[].adapter` = adapter.py 클래스명
- 이질적 데이터(시계열 등)는 **별도 target/model** 로 분리

## schema.py

```python
from datetime import date
from pydantic import BaseModel

class PangeaSchema(BaseModel):
    ticker: str
    company_name: str
    # ...
```

- 메인 클래스명 `PangeaSchema` 고정
- 타입: `str`, `int`, `float`, `bool`, `date`, `datetime` 만
- 필드명: 소문자 + `_`
- **필드명 `date` 사용 금지** — 타입 `date` 와 충돌. `trade_date`·`bas_dt` 등 사용

## adapter.py

```python
from abc import ABC, abstractmethod
from typing import Any, List

class BaseAdapter(ABC):
    @abstractmethod
    async def transform(self, data: List[dict[str, Any]], fields: List[str]) -> List[dict[str, Any]]:
        ...

class KisStockAdapter(BaseAdapter):
    async def transform(self, data, fields):
        ...
```

## unify.py

시그니처·저장 분담: [[data/pangea_output]]

**전체 샘플 (이 구조를 따른다. `...` 로 생략하지 말 것):**

[[data/example/unify]]

### unify 필수 사항

- **파일 소스는 필수가 아니다.** 입력 `sources` 에 `type=file` 이 있을 때만 `InMemoryDataBridge.get(did, source_id)` 로 키를 읽는다.
- **파일 없음(도구만)**: `SELECTED_TICKERS` 길이는 **user_query 의 종목 수와 같아야 한다.** 100종이면 100개. 샘플 빈 리스트·시총 상위 10개(005930 등)로 축소 금지.
- 파일이 있으면 파일 컬럼의 식별자를 쓴다. 파일이 있는데 시총 상위만 쓰기 금지.
- 도구 호출: `await call(tool_path, tool_name, tool_args)` — **Semaphore(2~5)** + CHUNK_SIZE 분할
- **MCP 호출 직후** `dump_tool_response(did, model, tool_path, key, raw_response)` — TTL 기준선 (원본 응답만)
- `status != SUCCESS` 이거나 call 예외 → **raise RuntimeError(메시지)** — `except Exception` 금지 (reporter 용 try/except·safe_report 포함)
- **reporter**: `if reporter: reporter.update(...)` 만. `safe_report` 정의·호출 금지 (report 태스크 전용)
- 통합 행이 0건이면 **raise** — `pd.DataFrame(columns=...)` 후 `state="completed"` 금지 (빈 parquet 이 보고서 원천이 됨)
- 통합 데이터는 메모리에서 DataFrame 구성 후 **return** — parquet 저장은 `handle_pangeaze` 가 수행
- `model` = `metadata.targets[].model`, `key` = 해당 target 의 `keys` 값 (복합키면 tuple)
- **진행 보고 필수** — [[report/reporter_progress]] 준수 (자주·자세히·한글·건수 포함)
- **mock·더미 데이터 금지** — 실제 call 결과 사용
- return dict 키는 target parquet stem (`stock_master`, `stock_prices` 등)

### dump 저장 예시

샘플 `[[data/example/unify]]` 의 `call` 직후 `dump_tool_response` 를 따른다.

### 데이터 저장 (런타임 분담)

1. **파일 소스** — `InMemoryDataBridge` (메모리, unify 입력용)
2. **도구 TTL** — unify 에서 `call` 직후 `dump_tool_response` (원본 응답만)
3. **통합 결과** — unify 가 `Dict[str, pd.DataFrame]` return
4. **parquet** — `handle_pangeaze` 가 return DataFrame 을 `{stem}.parquet` 로 저장
5. **이후 갱신** — `PangeaExDataFrame.queue_update` → `apply_pending_updates` (report data task)

### reporter (동기 — await 금지)

`reporter` 는 `TaskReporter` 입니다. **unify 에서는 `safe_report` 를 쓰지 않는다.**

```python
if reporter:
    reporter.update("[시작] 선정 종목 조회 시작", state="running")
    reporter.update("[조회] 종목 정보 (1/100)", state="running")
    reporter.update("[완료] 종목 기본정보·일별 수급 통합", state="completed")
```

- `PangeaSchema`·`MCP`·`InMemoryDataBridge`·함수명·`task_id` — progress **문자열에 금지**
- `10% 완료` 만 반복 **금지** — 단계 태그·종목명·건수 포함
- **0건을 completed 로 보고하지 말 것**

## 금지

- markdown 코드펜스로 JSON 감싸기 (structured output — 순수 JSON만)
- `unify_logic_code` / `adapter` / `schema_code` **중간 잘림**
- spec 에 없는 MCP tool name·args 추측
- `pd.DataFrame(columns=...)` 빈 프레임을 성공 return
- `except Exception: res = {}` 로 도구 FAIL 을 삼키기
- `except Exception` / `safe_report` 를 unify.py 에 넣기 (reporter 는 `if reporter:` 만)
- 입력에 파일 소스가 없는데 `InMemoryDataBridge.get` 으로 파일을 강제하기
- user_query 가 100종인데 시총 상위 10개만 SELECTED_TICKERS 에 넣기
