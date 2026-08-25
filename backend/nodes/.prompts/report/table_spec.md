# Table (visual table key)

컬럼 순서·밀도·핵심 수치 강조는 visual_design 규칙을 따른다.

TaskContext 저장 형식:

```json
{
  "header": ["지역", "매출(억)"],
  "dtypes": {"region": {"type": "string"}, "sales": {"type": "number", "decimals": 1}},
  "data": [{"region": "A", "sales": 120.5}]
}
```

- `header` 는 **반드시 한글 표시 라벨** — `sector` / `foreign_total` 등 **영문 필드명을 header 에 그대로 쓰지 말 것**
- `data[]` 행 dict 키·`dtypes` 키는 **영문 필드명** (코드용)
- `header[i]` 와 `data[]` 키는 **같은 인덱스**로 매핑 (`dtypes` 키 순서와 일치)
- **권장** 명시 매핑: `"columns": [{"key": "foreign_total", "label": "외국인 순매수"}, ...]`
- 각 컬럼 값은 upstream payload 의 **해당 필드**에서 가져올 것 — 식별자(id·code)를 이름·라벨 컬럼에 복사 **금지**
- raw 전체 row 금지 — 집계·스크린 결과만
- `{type:table, value:...}` 래퍼 금지
- (선택) `title`: 표가 보여주는 사실 (예: `"종목별 기관·외국인 순매수"`)
- 행이 12를 넘으면 상위/하위 또는 appendix 로 분리
- 핵심 지표 컬럼을 식별 컬럼 바로 다음에 둘 것
