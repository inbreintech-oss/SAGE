## [NameError]
- **최근 업데이트**: 2026-07-27 14:57:09
### [NameError] (execute) 반복 주의
* **원인**: NameError: name 'source_path' is not defined
* **준수 계약**: instruction.md + runtime_contract
* **수정**: 위 계약·validator 오류 메시지를 그대로 반영해 동일 contract 위반 금지
---
## [JsonLiteralInPythonValidator]
- **최근 업데이트**: 2026-07-27 16:46:46
### [JsonLiteralInPythonValidator] (codegen) 재시도 후 통과
* **원인**: JSON 리터럴 'true' 금지 — Python dict 에는 True 사용 (echarts_spec JSON 예시를 코드에 그대로 붙여넣지 말 것)
* **준수 계약**: runtime_contract — JSON true/false/null → True/False/None
* **수정**: instruction.md·validator 오류와 모순 없이 동일 contract 위반 금지
---
## [ValueError]
- **최근 업데이트**: 2026-07-27 19:32:12
### [ValueError] (execute) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: ValueError: Index contains duplicate entries, cannot reshape
* **준수 계약**: instruction.md + runtime_contract
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---
## [AttributeError]
- **최근 업데이트**: 2026-07-27 19:40:18
### [AttributeError] (execute) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: AttributeError: 'NoneType' object has no attribute 'get'
* **준수 계약**: instruction.md + runtime_contract
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---

## [UpstreamBoardValidator]
- **최근 업데이트**: 2026-07-27 19:40:18
### [UpstreamBoardValidator] (codegen) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: upstream context 가 있으나 칠판에 등록된 key 가 없음 — 선행 태스크 실행·저장 후 codegen 하거나 llm_attach payload key 사용
* **준수 계약**: upstream_context catalog·llm_attach payloads
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---