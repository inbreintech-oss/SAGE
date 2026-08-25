# Report Composition — 3안: type 세분화 + data.role

도메인 공통 문서 구성. `layout` 은 **구조·type·key** 만, **`data[key].role`** 은 lint·QA 용 의미 태그.

## Meta

| 필드 | 기본값 |
|------|--------|
| `template_id` | `analytical-standard` |
| `pattern_id` | `analytical-standard` |

## layout leaf type (세분화 · 권장)

| type | data.role (권장) | 용도 |
|------|------------------|------|
| `document_title` | `report_title` | 문서 제목 (`text`, `level: 1`) |
| `section_title` | `section_header` | 섹션 제목 (`level` ≥ 2) — **task_id·태스크명 금지** |
| `summary_card` | `executive_summary` | 핵심 요약 bullet 3~5 |
| `kpi_card` | `kpi_row` | KPI `items[]` |
| `insight_card` | `chart_insight` / `table_insight` / `key_findings` | 차트·표 직후 해석 |
| `text_card` | `methodology` 또는 `key_findings` | 일반 서술 |
| `closing_card` | `conclusions` | **결론·제언 — 문서 마지막 블록** |
| `metrics_table` | `metrics_table` | 집계 표 |
| `appendix_table` | `appendix_table` | 부록 표 |
| `primary_chart` | `primary_chart` | 주요 차트 |
| `secondary_chart` | `secondary_chart` | 보조 차트 |
| `rows` / `cols` | — | 컨테이너 |

**레거시** (하위 호환): `header`, `card`, `echart`/`chart`, `table` — 신규 산출은 세분화 type 사용.

## data.role 규칙

- `role` 은 **`data[key]` 안**에 둔다. `layout.blocks[].role` **사용 금지**.
- closed enum: `report_title`, `section_header`, `executive_summary`, `kpi_row`, `key_findings`, `chart_insight`, `table_insight`, `conclusions`, `methodology`, `metrics_table`, `appendix_table`, `primary_chart`, `secondary_chart`
- type 과 role 불일치 시 lint `type_role_mismatch` warning.

예:

```json
{ "type": "document_title", "key": "report_header" }
"report_header": {
  "role": "report_title",
  "text": "분석 보고서",
  "level": 1
}
```

## data.style (선택 · 표현 힌트)

`data[key].style` — 렌더 variant. **내용·수치와 분리**.

| 키 | 값 (closed enum) | 용도 |
|----|------------------|------|
| `variant` | `default`, `emphasis`, `muted`, `highlight`, `callout` | 카드·블록 강조 |
| `accent` | `ink`, `primary`, `gold`, `success`, `danger`, `muted` | 포인트 색 (visual_design 토큰) |
| `density` | `compact`, `normal`, `spacious` | 여백 |
| `border` | `true` / `false` | 테두리 — `section_title` 은 구분바용 `true` |

`layout.blocks[].style` 은 레이아웃(열 너비 등), `data[key].style` 은 **콘텐츠 표현**.

**상용 기본** (남발 금지):

- `document_title` → `{variant: emphasis, accent: ink, density: spacious}`
- `section_title` → `{variant: emphasis, accent: gold, border: true}`
- `summary_card` → `{variant: callout, accent: muted}`
- 핵심 insight **최대 1개** → `{variant: highlight, accent: gold}`
- `closing_card` → `{variant: emphasis, accent: ink}`
- `metrics_table` → `{density: compact, border: true}`

나머지 카드는 `default`/`muted`. highlight 남발 금지. 상세 톤·차트 색은 visual_design.

## 패턴: analytical-standard

밀도는 [[report/insight_craft]]. 표+차트만 두고 서사를 생략하지 말 것.

1. `document_title`
2. `summary_card` 또는 `kpi_card` — 모집단 + 핵심 발견 (고유명·숫자)
3. `section_title` (독자용 제목 — `task-...` 금지)
4. `metrics_table`
5. `insight_card` (`table_insight`) — **table 직후**
6. `primary_chart`
7. `insight_card` (`chart_insight`) — **chart 직후**
8. (선택) `secondary_chart` + `insight_card` (`chart_insight`)
9. (선택) `appendix_table` + `insight_card` (`table_insight`) 직후
10. `closing_card` (`conclusions`) — **반드시 마지막**

지표를 오해할 수 있으면 `text_card` (`methodology`) 를 요약 직후 한 장 넣는다. 모든 보고서에 고정 섹션을 복제하지 말 것.

2열: `layout_block(type="cols", blocks=[primary_chart_leaf, insight_card_leaf])`

## Meta title / description

- 루트 `title`·`document_title.text` 는 **짧은 보고서명** (plan.title 수준, 40자 내외)
- 루트 `description` 은 **한 줄 부제** — plan 설명·`초안`·작업 지시문 복사 **금지**
- `document_title` 블록이 있으면 루트 title 과 동일하게 맞출 것

## 콘텐츠 분리

- 집계 수치 → `metrics_table` / `appendix_table`
- 표 해석 → `insight_card` (`table_insight`) — 표 직후
- 차트 해석 → `insight_card` (`chart_insight`) — 차트 직후
- 결론·제언 → `closing_card` (`conclusions`) — 차트·표로 끝내지 말 것
- **conclusions 본문**: 계층이 필요하면 **중첩 ordered list** markdown 사용
  - 상위 항목: `1.` `2.` `3.` 한 단계 번호 목록
  - 하위 항목: 부모 항목 아래 **들여쓴 중첩 ordered list** (`1.` `2.` — depth마다 렌더러가 번호 부여)
  - 본문에 수동 번호 문자열 삽입 **금지** — 목록 구조로만 표현
  - bullet(`-`)만으로 결론 전체를 flat 나열하지 말 것 (`executive_summary` 등에 사용)
- **마크다운 볼드(`**...**`) 절제**: 수치·키워드에 `**` 과다 사용 금지. 카드당 정말 중요한 **1~2곳만** 볼드. 나머지는 평문
- card `title` 과 content `##` 중복 금지
- 섹션 제목·카드 제목에 **내부 task_id** 노출 금지 (`task_boundary_visible` lint)

## narrative API

1. `attach_catalog_visuals(...)` — chart/table → `primary_chart`/`metrics_table` type + `data.role` 자동
2. `add_block(data, type=..., key=..., payload={..., "role": ..., "style": {...}?})` — role·style 은 payload·lint 용
3. `build_report_document(..., template_id="analytical-standard", ...)`

[[report/patterns/analytical-standard]]
