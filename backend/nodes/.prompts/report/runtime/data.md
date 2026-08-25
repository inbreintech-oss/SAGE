# Runtime — type: data

## Pangea · MCP

| API | 용도 |
|-----|------|
| `PangeaExDataFrame(did=task.data_id).to_pandas(model)` | 통합 원본 — `dataset_context` [PANGEA TARGETS] model 만 |

MCP 갱신 흐름 (상세·예시 코드):

[[report/example/pangea_api]]

비즈니스 규칙 (하드코딩 금지·plan_updates):

[[report/data_anti_hardcode]]

## ctx.update_task (data 전용)

- plan task `instruction` 의 key 로 **집계·선정 dict/list** 저장 (최소 1회)
- 공통 금지(`to_dict(records)` 등) → `runtime_contract` validator-synced 절

`llm_attach`: root data 는 보통 선행 없음.
