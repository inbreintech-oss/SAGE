# ReportDocument — 산출 파일·TaskContext key

## 디스크 산출 (`reports/{rid}/`)

| 파일 | 단계 | 설명 |
|------|------|------|
| `draft.json` | narrative | 초안 ReportDocument (`report_document` key) |
| `report.json` | release | 최종 출판본 (`report` key + `release_summary`) |

TaskContext key(`report_document`, `report`)와 파일명(`draft.json`, `report.json`)은 구분한다.

## root JSON (`draft.json` / `report.json` 공통)

| 필드 | 설명 |
|------|------|
| `title`, `description`, `template_id`, `pattern_id`, `version` | 메타 (`template_id` 기본 `analytical-standard`) |
| `plan_id`, `did`, `rid` | 식별자 |
| `layout` | `{ type: "rows"\|"cols", blocks: [...] }` |
| `data` | key → payload (**`description` 포함**) |
| `tasks` | task_id → `{ status, keys: [string] }` |
| `release_summary` | *(report.json 만)* release QA 변경 요약 — 아래 |
| `generation` | *(report.json 만)* 작성 시각·소요·문자 수·LLM 토큰 — 아래 |
| `quality` | *(report.json 만, 선택)* 구성 품질 lint 점수·이슈 — 아래 |

## `generation` (report.json 전용)

runner 가 `collect_report_result` 시 root 에 병합 (plan codegen + task codegen 전체 LLM 사용량 포함).

```json
{
  "started_at": "2026-06-16T03:00:00+00:00",
  "completed_at": "2026-06-16T03:05:23+00:00",
  "duration_sec": 323.45,
  "characters": {
    "text": 12500,
    "json_file": 89000
  },
  "tokens": {
    "input": 100000,
    "output": 25000,
    "total": 125000,
    "calls": 12,
    "by_model": {
      "gemini-3.5-flash": { "input": 100000, "output": 25000, "total": 125000, "calls": 12 }
    }
  }
}
```

| 필드 | 설명 |
|------|------|
| `started_at` / `completed_at` | 파이프라인 시작·`report.json` 저장 시각 (UTC ISO) |
| `duration_sec` | 시작부터 release 완료까지 경과(초) |
| `characters.text` | layout·data 본문(제목·카드·표·차트 제목) 문자 수 |
| `characters.json_file` | `generation` 포함 최종 `report.json` 직렬화 길이 |
| `tokens.input` / `output` / `total` | LLM API usage 합계 (plan + task codegen + 재시도) |
| `tokens.calls` | LLM 호출 횟수 |
| `tokens.by_model` | 모델별 breakdown |

## `release_summary` (report.json 전용)

release executor 가 `ctx.update_task(..., key="release_summary", ...)` 로 저장 → runner 가 `report.json` root 에 병합.

```json
{
  "overview": "QA 한 줄 요약",
  "changes": [
    {
      "area": "data",
      "key": "executive_summary",
      "action": "edited",
      "note": "placeholder 문구 제거, 수치 표현 정정"
    }
  ]
}
```

| 필드 | 설명 |
|------|------|
| `overview` | 전체 QA 요약 (1–3문장) |
| `changes[]` | 항목별 수정 내역 |
| `changes[].area` | `data` \| `layout` \| `text` \| `meta` |
| `changes[].key` | `data`/`layout` 블록 key 또는 필드명 |
| `changes[].action` | `added` \| `removed` \| `edited` \| `fixed` |
| `changes[].note` | 무엇을·왜 수정했는지 |
| `changes[].task_id` | 소스를 갱신한 upstream task_id |

## `quality` (report.json 전용, runner 자동)

```json
{
  "score": 85,
  "passed": true,
  "issues": [
    {"level": "warning", "code": "missing_chart_insight", "message": "..."}
  ]
}
```

## layout leaf

리프 블록: `type`, `key`, `task_id?`, `style?` — **`layout.blocks[].role` 사용 금지**. 의미 태그는 **`data[key].role`**.

### 세분화 type (권장)

| type | data[key] |
|------|-----------|
| `document_title` | `{ role: "report_title", text, level?: 1, description? }` |
| `section_title` | `{ role: "section_header", text, level?: 2\|3, description? }` |
| `summary_card` | `{ role: "executive_summary", title?, content, content_type?, description? }` |
| `kpi_card` | `{ role: "kpi_row", items: [{label,value,delta?}], title?, description? }` |
| `insight_card` | `{ role: "chart_insight"\|"table_insight"\|"key_findings", title?, content, content_type?, style?, description? }` |
| `text_card` | `{ role: "methodology"\|"key_findings", title?, content, content_type?, style?, description? }` |
| `closing_card` | `{ role: "conclusions", title?, content, content_type?, style?, description? }` |
| `metrics_table` | `{ role: "metrics_table", header, dtypes, data, title?, style?, description? }` |
| `appendix_table` | `{ role: "appendix_table", header, dtypes, data, title?, style?, description? }` |
| `primary_chart` | `{ role: "primary_chart", ...ECharts option, style?, description? }` |
| `secondary_chart` | `{ role: "secondary_chart", ...ECharts option, style?, description? }` |
| `rows`/`cols` | container — `blocks[]` 만 |

### 레거시 type (하위 호환)

| type | data[key] |
|------|-----------|
| `header` | `{ role?, text, level?, description? }` |
| `card` | `{ role?, title, content, content_type?, card_type?, items?, description? }` |
| `echart`/`chart` | `{ role?, ...ECharts option, description? }` |
| `table` | `{ role?, header, dtypes, data, title?, description? }` |

### `data.role` (lint · closed enum)

`report_title` | `section_header` | `executive_summary` | `kpi_row` | `key_findings` | `chart_insight` | `table_insight` | `conclusions` | `methodology` | `metrics_table` | `appendix_table` | `primary_chart` | `secondary_chart`

### `data.style` (선택 · 표현 힌트)

`data[key].style` — 렌더 variant. closed keys: `variant` (`default`|`emphasis`|`muted`|`highlight`|`callout`), `accent` (`ink`|`primary`|`gold`|`success`|`danger`|`muted`), `density` (`compact`|`normal`|`spacious`), `border` (boolean). lint `data_style_invalid`. 적용표·차트 팔레트는 visual_design.

[[report/core/composition]]

## 태스크 산출 key (TaskContext)

| type | key |
|------|-----|
| narrative | `report_document` → **`draft.json`** |
| release | `report` → **`report.json`**, `release_summary` |
| release (디스크) | `apply_upstream_patches` → **`srcs/{upstream_tid}.py` 최종본** |

## release → upstream 소스

조회·재실행은 **`srcs/*.py` 만** 실행된다. release QA 는 **메모리 patch 만으로 끝나면 무의미**.

1. draft `data` patch
2. `ctx.update_task(narrative_tid, key="report_document", ...)` — ctx 동기화
3. `apply_upstream_patches(rid, {tid: [ops]})` — `{tid: []}` 또는 old/new snippet patch (전체 embed 금지)

[[report/example/release_api]]

## layout API (narrative/release)

[[report/example/layout_api]]

## report_document 예제 (초안 스키마)

[[report/example/report_document]]
