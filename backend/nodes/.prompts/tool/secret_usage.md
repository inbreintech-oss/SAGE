# SecretKey 사용 (도구 code)

외부 API 키가 필요하면:

1. 키 값을 소스에 쓰지 말 것. `os.environ` 금지.
2. generate 로 주입된 `SECRET_ID` 로만 조회.

```python
from sage.secret import get_secret

SECRET_ID = "sk-..."  # generate 가 넣는 값. 바꿔 쓰지 말 것

@mcp.tool(name="fetch_vendor_data")
async def fetch_vendor_data(request: VendorRequest) -> VendorResponse:
    APP_KEY = await get_secret("APP_KEY", secret_id=SECRET_ID)
    APP_SECRET = await get_secret("APP_SECRET", secret_id=SECRET_ID)
```

`get_secret` 을 쓰는 도구 함수는 **async def**.

등록되지 않은 key_name (`API_TOKEN` 등) 을 `require_secret` 하지 말 것. user 프롬프트의 key_name 목록만 사용.

## assetize 된 공유 경로 도구만

`get_secret_for_tool("APP_KEY", "kis/investor")` 는 **이미 배포된 경로**용이다.  
`tool/generate` 초안(`tm-*`)에 다른 도구 경로를 넣지 말 것.
