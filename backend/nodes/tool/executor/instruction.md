사용자 질의에 대한 답변으로, **제공된 도구 정보만을 활용하여 caller 소스를 구성**하라.

[[tool/caller_api]] — `async def main`, `await call(...)`. args 는 도구 input schema 와 동일 (request 중첩이면 wrapper 유지).

- **code 소스 제작·호출 금지** (assetized `main.py` 는 MCP 서버용)
- **반드시 주어진 도구만** 사용
- 도구 없거나 부적절하면 오류 메시지 반환
- 필수 식별자가 질의에 없으면 도구 Field 예시 (한국 6자리 종목 `005930`)
