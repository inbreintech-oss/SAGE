# Tool caller — exec 계약 (docker_pool)

`caller.py` 만 생성. `main.py` import 금지.

```python
async def main(**kwargs):
    raw = await call("도구경로", "tool_name", args)
    return raw
```

`args` 는 MCP input schema 와 동일:

- 함수가 `request: Model` 이면 `{"request": {"필드": "값"}}` — 펼치지 말 것
- 최상위 필드면 flat dict
- spec 에 없는 키 금지
- 종목이 질의에 없으면 `005930`

JSON-serializable 만 반환.
