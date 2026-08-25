## [TaskExecutorPatternsValidator]
- **최근 업데이트**: 2026-06-19 13:27:28
### 검증 위반 원인 및 수정 포인트
* **위반 원인**: Upstream raw row·전체 JSON 을 downstream(`ctx.update_task`)으로 그대로 전달.
* **수정 포인트**: 집계·요약만 `ctx.update_task` — raw row list 금지.
---
## [PydanticValidator]
- **최근 업데이트**: 2026-06-26 16:37:01
### 검증 위반 원인 및 수정 포인트
* **위반 원인**: 응답에 markdown 코드 블록(```json) 포함 → JSON 파싱 실패.
* **수정 포인트**: 순수 JSON 객체(`{}`)만 출력.
---
## [NameError]
- **최근 업데이트**: 2026-07-27 10:56:44
### [NameError] (execute) 재시도 후 통과
* **원인**: NameError: name 'add_block' is not defined
* **준수 계약**: instruction.md + runtime_contract
* **수정**: 위 계약·validator 오류 메시지를 그대로 반영해 동일 contract 위반 금지
---
## [UpstreamBoardValidator]
- **최근 업데이트**: 2026-07-27 15:29:51
### [UpstreamBoardValidator] (codegen) 재시도 후 통과
* **원인**: get_result key 'selected_stocks_summary' 가 upstream 칠판에 없음. 허용 key: ['market_cap_chart', 'sector_per_chart', 'valuation_analysis_summary'] — llm_attach upstream_payloads 참고
* **준수 계약**: upstream_context catalog·llm_attach payloads
* **수정**: 위 계약·validator 오류 메시지를 그대로 반영해 동일 contract 위반 금지
---
## [JsonLiteralInPythonValidator]
- **최근 업데이트**: 2026-07-27 17:49:34
### [JsonLiteralInPythonValidator] (codegen) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: JSON 리터럴 'true' 금지 — Python dict 에는 True 사용 (echarts_spec JSON 예시를 코드에 그대로 붙여넣지 말 것)
* **준수 계약**: runtime_contract — JSON true/false/null → True/False/None
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---

## [NarrativeTaskValidator]
- **최근 업데이트**: 2026-07-27 19:42:28
### [NarrativeTaskValidator] (codegen) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: get_result(task_id, key) 에 task_id 문자열 하드코딩 금지 — task.context[i] 또는 task.context 를 순회한 변수 사용
* **준수 계약**: instruction.md + runtime_contract + validator 메시지
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---