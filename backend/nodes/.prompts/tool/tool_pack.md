# ToolPack

| 필드 | 설명 |
|------|------|
| `tool_id` | `tm-{name}-{uuid8}` |
| `title` / `description` | 역할 요약 |
| `code` | FastMCP + pydantic v2 MCP 도구 소스 |
| `caller` | 도구를 호출해 질의에 답하는 실행 코드 |
| `query_examples` | 한국어 질의 3개 (도구 id·API 경로 나열 금지) |

## code

- `@mcp.tool` + Request/Response 모델. HTTP·secret 이면 `async def`.
- 질의에 적힌 TR_ID·URL 은 상수. `SECRET_ID` 는 프롬프트 값 그대로.
- 벤더/HTTP 실패는 `raise`. 빈 성공 응답으로 숨기지 말 것.
- 하단 `mcp.run(log_level='ERROR', show_banner=False)`.

## caller

[[tool/caller_api]]

generate 초안이면 `call` path 는 이 `tool_id`. exec 이면 요청 tools[] / spec `tool_path`.
