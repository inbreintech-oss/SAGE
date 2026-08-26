# Plan

입력: `query`, `data_id`, `tools`. `dataset_context` 는 enrich.

`tasks[]` 는 DAG. `context` = 선행 `task_id`. 배열 순서 ≠ 실행 순서.

| type | 역할 |
|------|------|
| `data` | 원천 준비. root 는 `context: []` |
| `analyze` | 집계·파생 |
| `visual` | 차트·표 |
| `narrative` | 보고서 초안 |
| `release` | QA·출판. context 에 narrative·visual 및 narrative 의 선행 전부 |

`instruction` 은 실행 LLM 미션 (한글). 질의의 규모(종목 수·기간)는 각 instruction 에 남긴다. 클래스명·layout·MCP 함수명을 plan 에 넣지 말 것.
