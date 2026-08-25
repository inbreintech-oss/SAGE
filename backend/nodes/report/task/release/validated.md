## [UpstreamBoardValidator]
- **최근 업데이트**: 2026-07-13 13:16:55
### 위반 원인 및 수정 포인트
* **위반 원인**: 칠판에 없는 key 로 `get_result` 호출.
* **수정 포인트**: upstream_context catalog·llm_attach payload 의 **허용 key만** 사용.
---
## [TaskCodeSyntaxValidator]
- **최근 업데이트**: 2026-07-14 15:16:17
* **위반 원인**: 생성된 Python 소스코드 내부에서 문자열 리터럴을 정의하는 따옴표가 쌍을 이루지 못하고 도중에 끊겨 구문 오류가 발생했습니다.
* **위반 원인**: 주로 여러 줄에 걸친 마크다운 텍스트나 중첩된 JSON 형태의 문자열을 작성할 때, 시작 따옴표와 매칭되는 닫는 따옴표가 누락되어 발생합니다.
* **위반 원인**: 문자열 내부에서 이스케이프 처리되지 않은 따옴표가 사용되어 문자열이 의도치 않게 조기에 종료된 것으로 인식되었습니다.
* **수정 포인트**: 모든 문자열 리터럴의 시작과 끝에 사용된 따옴표(단일, 이중, 삼중 따옴표)가 정확히 대칭을 이루며 닫혀 있는지 전수 점검합니다.
* **수정 포인트**: 문자열 내부에서 동일한 종류의 따옴표가 사용될 경우 백슬래시를 활용해 안전하게 이스케이프 처리하거나 서로 다른 따옴표를 교차 적용합니다.
---
## [PydanticValidator]
- **최근 업데이트**: 2026-07-27 19:34:59
### [PydanticValidator] (codegen) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: "code": "async def run_task(task, ctx, reporter=None):\n    safe_report(reporter, '[검토] 보고서 초안 및 시각화 자료 검증 시작', state='running')\n    narrative_tid = task.context[0]\n    draft = ctx.get_result(narrative_tid, 'report_document')\n    safe_report(reporter, '[검토] 보고서 텍스트 가독성 개선 및 오탈자 수정 중', state='running')\n    draft['data']['executive_summary']['content'] = (\n        '- **시장 규모 및 밸류에이션**: 분석 대상 50개 종목의 총 시가총액은 약 3,953조 원이며, 전체 평균 PER은 212.48배, PB
* **준수 계약**: instruction.md + runtime_contract + validator 메시지
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---
## [TaskExecutorPatternsValidator]
- **최근 업데이트**: 2026-07-27 19:53:29
### [TaskExecutorPatternsValidator] (codegen) 반복 주의
* **원인**: progress 메시지에 내부 용어 금지 ([출판] upstream 소스 최종본 반영 중…) — 사용자 친화 한글만 ([데이터][조회][분석] 등, reporter_progress.md)
* **준수 계약**: runtime_contract codegen_contract (validator-synced)
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---

## [ReleaseTaskValidator]
- **최근 업데이트**: 2026-08-22 15:15:16
### [ReleaseTaskValidator] (codegen) 재시도 후 통과 — 동일 위반 재발 금지
* **원인**: release: ctx.update_task(..., key="report", ...) 또는 report=... 필요 (runner → report.json, legacy: ['report', 'layout', 'report_layout'])
* **준수 계약**: release/instruction.md 7번·release_contract
* **재발 방지**: instruction.md·runtime_contract 와 모순 없이, 위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)
---