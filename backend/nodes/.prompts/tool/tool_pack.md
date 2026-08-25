# ToolPack

사용자 질의 목적에 맞는 ToolPack 도구를 생성하는 것이 목적이다.

## 필드

| 필드 | 설명 |
|------|------|
| `tool_id` | `tm-{name}-{uuid8}` (소문자·하이픈, 최대 30자 권장) |
| `title` | 도구 제목 |
| `description` | 역할·입력·출력(Pydantic 모델) 요약 |
| `code` | FastMCP + pydantic v2 기반 MCP 도구 전체 소스 |
| `caller` | 도구 호출 소스 (검증·실행용) |
| `query_examples` | **정확히 3개** — `/tool/exec` 자연어 문장 |

- **tool_id**: `^tm-[a-z]+-[a-z]+(-[a-z]+)?-[a-z0-9]{8}$` (최대 30자)
- 예: `tm-data-extractor-a1b2c3d4`

### [MUST-FOLLOW] code

- FastMCP + pydantic v2. `@mcp.tool(name="...")`. `**kwargs` 금지 — Request 모델.
- 반환은 Pydantic Response. numpy/pandas 스칼라는 Python native.
- **secret_id 또는 HTTP 가 있으면 `@mcp.tool` 은 `async def`.**
- 질의의 TR_ID / URL 경로는 상수. `SECRET_ID` 는 user 프롬프트 값 그대로 (예시 문자열로 바꾸지 말 것).
- 벤더 실패코드·HTTP 오류는 `raise RuntimeError`. 빈 `items=[]` 로 성공 처리 금지.
- caller: `await call(tool_id, tool_name, args)`. Request 파라미터면 `{"request": {...}}`.
- 하단:

```python
if __name__ == '__main__':
    mcp.run(log_level='ERROR', show_banner=False)
```

### query_examples

도구 기능을 담은 한국어 문장 3개. 도구 id·API 경로 나열 금지.

## 응답 예시 — secret_id 가 있을 때 (이것을 복사)

```yaml
tool_id: "tm-vendor-quotes-a1b2c3d4"
title: "시세 조회"
description: "등록된 비밀키로 벤더 REST 를 호출한다"
code: |
  import httpx
  from fastmcp import FastMCP
  from pydantic import BaseModel, Field
  from sage.data.kis_auth import KIS_BASE_URL, get_kis_access_token
  from sage.secret import get_secret

  mcp = FastMCP("VendorQuotes")
  SECRET_ID = "sk-..."  # user 프롬프트 secret_id 와 동일
  TR_ID = "질의 TR_ID 그대로"
  API_PATH = "질의 URL 경로 그대로"

  class QuotesRequest(BaseModel):
      fid_cond_mrkt_div_code: str = Field("J", description="시장 분류")
      fid_input_iscd: str = Field("005930", description="종목코드 6자리")

  class QuotesResponse(BaseModel):
      status: str
      message: str
      items: list

  @mcp.tool(name="get_quotes")
  async def get_quotes(request: QuotesRequest) -> QuotesResponse:
      APP_KEY = await get_secret("APP_KEY", secret_id=SECRET_ID)
      APP_SECRET = await get_secret("APP_SECRET", secret_id=SECRET_ID)
      token = await get_kis_access_token()
      headers = {
          "content-type": "application/json; charset=utf-8",
          "authorization": f"Bearer {token}",
          "appkey": APP_KEY,
          "appsecret": APP_SECRET,
          "tr_id": TR_ID,
          "custtype": "P",
      }
      params = {
          "FID_COND_MRKT_DIV_CODE": request.fid_cond_mrkt_div_code,
          "FID_INPUT_ISCD": request.fid_input_iscd,
      }
      async with httpx.AsyncClient(timeout=15.0) as client:
          resp = await client.get(f"{KIS_BASE_URL}{API_PATH}", headers=headers, params=params)
      resp.raise_for_status()
      data = resp.json()
      if str(data.get("rt_cd")) not in ("0", "00"):
          raise RuntimeError(data.get("msg1") or "vendor error")
      rows = data.get("output") or []
      return QuotesResponse(status="SUCCESS", message="ok", items=rows)

  if __name__ == '__main__':
      mcp.run(log_level='ERROR', show_banner=False)

caller: |
  import asyncio, json
  from sage.mcp import call

  async def main():
      return await call(
          "tm-vendor-quotes-a1b2c3d4",
          "get_quotes",
          {"request": {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": "005930"}},
      )

  if __name__ == '__main__':
      print(json.dumps(asyncio.run(main()), ensure_ascii=False, indent=2))
```

비밀키가 **없을 때만** sync 로컬 도구가 허용된다. HTTP 도구에 `def analyze_weather` 골격을 복사하지 말 것.
