## [PlanStructureValidator]
- **최근 업데이트**: 2026-07-28 13:36:32
### [PlanStructureValidator] (codegen) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: release 태스크 context 에 narrative·visual 및 narrative 선행 태스크가 필요합니다.
* **준수 계약**: release.context ⊇ 모든 narrative·visual + narrative 의 context
* **재발 방지**: release 의 context 에 narrative·visual 과 narrative 가 가리키는 선행 task_id 를 빠짐없이 넣는다.
---
