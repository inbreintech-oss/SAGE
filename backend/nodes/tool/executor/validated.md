## [ToolAccessValidator]
- **최근 업데이트**: 2026-08-26 16:22:50
### [ToolAccessValidator] (codegen) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: 허용되지 않은 도구 'tm-kis-investor-f765755d' 호출이 감지되었습니다. 현재 사용 가능한 도구 목록은 ['kis/investor'] 입니다.
* **준수 계약**: call() 첫 인자 = 요청 tools[] / spec tool_path. tm-* generate id 금지
* **재발 방지**: await call() 첫 인자를 ['kis/investor'] 중 하나로 바꿔라. 'tm-kis-investor-f765755d' 삭제. generate 초안 tm-* id 는 허용 목록에 없으면 금지.
---
