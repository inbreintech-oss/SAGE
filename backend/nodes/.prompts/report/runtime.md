# p2 Task Runtime (index)

태스크 codegen enrich `runtime_contract` = **type별 slice** 조합 (`sage/prompt/report_prompts.py`).

| type | slice |
|------|--------|
| `data` | core + data |
| `analyze` | core + upstream |
| `visual` | core + upstream |
| `narrative` | core + narrative |
| `release` | core + release |

전체 조합 미리보기는 `_scripts/measure_report_prompts.py` 참고.

## slice 파일

- [[report/runtime/core]]
- [[report/runtime/data]]
- [[report/runtime/upstream]]
- [[report/runtime/narrative]]
- [[report/runtime/release]]
