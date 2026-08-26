# caller.py

`from sage.mcp import call` 후 `await call(path, name, args)`.
path·name·args 는 제공된 도구 spec. 워커는 `call` 을 인자로 넘기지 않는다.

```python
from sage.mcp import call

async def main(**kwargs):
    ...  # spec 대로 호출하고, 질의에 맞게 결과를 정리해 JSON 으로 반환
```

질의에 답하는 코드를 짠다. 도구가 더 긴 시계열·목록을 줘도 질의가 더 좁으면 그에 맞게 줄인다.
JSON-serializable 만 반환.
