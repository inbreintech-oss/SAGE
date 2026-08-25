## [LlmImportForbiddenValidator]
- **최근 업데이트**: 2026-07-27 10:35:00
### 위반 원인 및 수정 포인트
* **위반 원인**: executor body 에 `import`/`from` 작성.
* **수정 포인트**: import 없이 `call`, `PangeaExDataFrame`, `safe_report` 등 prelude 심볼만 사용.
---
## [SchemaContract]
- **최근 업데이트**: 2026-07-14 15:25:55
### [SchemaContract] (execute) 재시도 후 통과
* **준수 계약**: dataset_context schema.py [SCHEMA DATA TYPES]
* **수정**: 위 계약·validator 오류 메시지를 그대로 반영해 동일 contract 위반 금지
---
## [DataTaskFlowValidator]
- **최근 업데이트**: 2026-07-27 14:25:00
### [DataTaskFlowValidator] (codegen) 재시도 후 통과
* **원인**: - to_pandas(model)
* **준수 계약**: runtime_contract data 흐름
* **수정**: 위 계약·validator 오류 메시지를 그대로 반영해 동일 contract 위반 금지
---
## [AttributeError]
- **최근 업데이트**: 2026-07-27 17:05:56
### [AttributeError] (execute) 반복 주의
* **원인**: AttributeError: 'DataTask' object has no attribute '_flush_lesson_accumulator_async'
* **준수 계약**: instruction.md + runtime_contract
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---

## [TaskExecutorPatternsValidator]
- **최근 업데이트**: 2026-08-22 16:30:15
### [TaskExecutorPatternsValidator] (codegen) 반복 주의
* **원인**: raw row json(to_dict records) downstream 전달 금지
* **준수 계약**: runtime_contract codegen_contract (validator-synced)
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---