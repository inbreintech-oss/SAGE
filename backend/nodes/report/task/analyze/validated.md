## [ImportPathValidator]
- **최근 업데이트**: 2026-07-14 14:15:45
* **위반 원인**: 코드 내부에서 특정 컨텍스트 객체를 참조하거나 사용하였으나, 검증기(`ImportPathValidator`)가 필수적으로 요구하는 모듈 임포트 선언문이 누락되어 예외가 발생했습니다.
* **검증 매커니즘**: 검증 소스코드는 코드 내 특정 패턴이 감지되면 이에 대응하는 필수 임포트 구문이 존재하는지 정규표현식으로 검사하며, 일치하는 구문이 없을 경우 오류를 발생시킵니다.
* **수정 포인트**: 해당 컨텍스트 객체를 사용하는 소스코드 파일의 최상단에 검증기가 요구하는 정확한 패키지 경로의 임포트 선언문을 추가해야 합니다.
* **주의 사항**: 임포트 경로 작성 시 오탈자가 없어야 하며, 검증 규칙에 정의된 모듈 경로를 정확히 일치시켜야 정상적으로 검증을 통과할 수 있습니다.
---

## [TaskExecutorPatternsValidator]
- **최근 업데이트**: 2026-08-26 16:48:29
### [TaskExecutorPatternsValidator] (codegen) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: raw row json(to_dict records) downstream 전달 금지
* **준수 계약**: runtime_contract codegen_contract (validator-synced)
* **재발 방지**: `to_dict(orient='records')` / `to_dict('records')` 를 지운다. ctx.update_task value 는 집계 dict/list 만.
---