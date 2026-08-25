## [ToolAccessValidator]
- **최근 업데이트**: 2026-08-22 14:23:36
### [ToolAccessValidator] (codegen) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: 허용되지 않은 도구 'tm-samsung-sugup-e8f9a1b2' 호출이 감지되었습니다. 현재 사용 가능한 도구 목록은 ['tm-kis-investor-f765755d', 'tm-kis-token-manager-b9e3f2a1'] 입니다. 코드(code) 섹션에서 정의한 내부 함수는 caller에서 직접 call()로 호출할 수 없습니다.
* **준수 계약**: instruction.md + runtime_contract + validator 메시지
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---