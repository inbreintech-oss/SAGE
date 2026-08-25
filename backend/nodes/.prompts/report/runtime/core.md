# Task Runtime — core (모든 type)

태스크 **executor Python** codegen. Plan JSON 에 구현명 넣지 않음.

## enrich (LLM prompt 필드)

| 필드 | 내용 |
|------|------|
| `runtime_contract` | type slice + **Codegen executor rules (validator-synced)** + task shell |
| `instruction` | **type별 미션·API 흐름** (이 파일과 중복 금지) |
| `dataset_context` | Pangea 스키마·프로파일 (`samples` 는 참고용) |
| `upstream_context` | TaskContext key catalog |
| `llm_attach` | upstream json payload (집계·선별만) |

- 공통 금지·TaskContext·progress·import 규칙 → **`runtime_contract` 내 validator-synced 절** (소스: `sage/report/codegen_contract.py`)
- instruction 은 **type 전용** 규칙만 (data MCP 흐름, visual echarts, release patch 등)

## TaskRun · 응답 JSON

[[report/example/run_task]]

`task_id`, `title`, `description`, `code` — **import 없이** `async def run_task` + helper.

## Reporter

[[report/reporter_progress]]
