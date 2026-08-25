# MCP 도구 (Tools)

SAG-E에서 **도구**는 FastMCP 서버(`main.py`)와 자연어 실행기(`caller.py`) 한 쌍입니다.  
Pangea 통합, 보고서 태스크 codegen, `/tool/exec` 모두 동일한 MCP 경로를 참조합니다.

---

## 생명주기

```
POST /tool/generate (SSE)
    → tm-{name}-{uuid8}/  (main.py + caller.py + metadata.json)
    → execute_with_fix (smoke test, Self-Healing)

POST /tool/assetize
    → tools/{asset_path}/  (예: kis/stock)
    → metadata.status = "assetized"
    → MCP 게이트웨이(8091) HTTP mount

Pangea / Report / tool/exec 에서 path 로 참조
```

| status | 의미 |
|--------|------|
| `generated` | codegen 직후 |
| `syntax-passed` | 문법 검증 통과 |
| `validated` | smoke caller 실행 성공 |
| `assetized` | MCP HTTP 노출 — **Pangea·plan에서 사용 가능** |
| `failed` | 검증·실행 실패 |

---

## 디렉터리 구조

```
tools/
└── {namespace}/{function}/     # asset_path (예: kis/stock, yf/fx-rate)
    ├── main.py                 # @mcp.tool 데코레이터 — MCP 서버
    ├── caller.py               # async def main(**kwargs) — NL 실행 진입점
    └── metadata.json           # status, instructions, query_examples
```

**임시 도구** (`tool/generate` 결과):

```
tools/tm-{name}-{uuid8}/
```

assetize 시 `asset_path`로 복사·승격하거나 동일 경로에 status만 갱신합니다.

---

## 식별자 규칙

| 형식 | 예 | 설명 |
|------|-----|------|
| `{ns}/{fn}` | `kis/stock`, `yf/fx-rate` | assetize된 정식 경로 |
| `tm-{name}-{id8}` | `tm-corr-analysis-a1b2c3d4` | generate 직후 임시 ID |

### Namespace (권장)

| Namespace | 예 | 설명 |
|-----------|-----|------|
| **kis** | `kis/stock` | 한국투자증권 API |
| **yf** | `yf/fx-rate`, `yf/commodity` | yfinance |
| **anly** | `anly/fin/timeseries-stat` | 시계열·통계 분석 |
| **pubd** | `pubd/search-api` | 공공데이터 OpenAPI 검색 |
| **sage** | (내부) | 프레임워크 내장 유틸 |

> 저장소 기본 `tools/` 폴더는 비어 있을 수 있습니다. `generate` + `assetize` 또는 수동 배치 후 사용합니다.

---

## main.py (MCP 서버)

FastMCP `@tool` 함수를 정의합니다. Pydantic 모델·dict/list 등 JSON 직렬화 가능한 결과를 반환해야 합니다.

```python
from fastmcp import FastMCP

mcp = FastMCP("kis-stock")

@mcp.tool
def get_stock_detail(itcode: str) -> dict:
    """종목 상세 재무 정보."""
    ...

if __name__ == "__main__":
    mcp.run()
```

---

## caller.py (자연어 실행)

`/tool/exec` 및 executor 노드가 동적으로 로드합니다.

```python
async def main(**kwargs):
    # kwargs: LLM이 추론한 tool 인자
    ...
    return {"result": ...}   # JSON 직렬화 가능
```

`finalize_caller_source`가 `get_transport_path('logical-name')` 호출을 실제 `tm-*` ID로 치환합니다.

---

## API 사용

### exec — 자연어 도구 호출

`POST /tool/exec`

```json
{
  "query": "미국 달러 환율 3개월 시계열 분석",
  "tools": ["yf/fx-rate", "anly/fin/timeseries-stat"]
}
```

내부: `nodes/tool/executor` → caller codegen → `execute_caller_with_fix`

### generate — 새 도구 codegen

`POST /tool/generate` (SSE)

```json
{
  "query": "두 종목 수익률 상관관계를 계산하는 도구",
  "category": "finance",
  "secret_id": "sk-a1b2c3d4",
  "ref_code": "..."
}
```

### assetize — MCP 노출

`POST /tool/assetize`

```json
{
  "tool_id": "tm-corr-analysis-e8a7c2b5",
  "asset_path": "anly/fin/correlation",
  "title": "Correlation Analysis",
  "description": "Pearson 상관계수 계산"
}
```

응답 `asset_path`가 이후 모든 API에서의 도구 ID입니다.

### recommend — 데이터셋 기반 추천

`POST /tool/recommend`

```json
{
  "did": "did-fx-report-1bab8d81",
  "tool_category": "finance"
}
```

---

## MCP 게이트웨이

`main.py` 기동 시 별도 프로세스로 **8091** 포트에 MCP 게이트웨이가 올라갑니다.

- `metadata.status == "assetized"` 인 `tools/**/main.py` 만 mount
- Pangea `sources[].path`, report `tools[]`, `sage.mcp.call(path, ...)` 에서 동일 경로 사용
- stdio transport: assetize되지 않은 로컬 `main.py` 직접 실행도 지원

---

## Secret 키 연동

외부 API 도구는 `/secret/register`로 키를 등록하고, generate/update 시 `secret_id`를 넘깁니다.  
codegen attach에 키 이름만 포함되며 **값은 암호화 저장**됩니다.

---

## 참고

- OpenAPI 예제: http://127.0.0.1:8090/docs → `/tool/*`
- 노드별 도구 codegen 규칙: [nodes/tool/generator/instruction.md](../nodes/tool/generator/instruction.md)
- Pangea에서 tool 소스 사용: [nodes/data/pangeaze/instruction.md](../nodes/data/pangeaze/instruction.md)
