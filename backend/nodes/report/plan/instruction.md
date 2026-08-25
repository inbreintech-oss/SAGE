# Plan JSON (DAG blueprint)

입력: `query`, `data_id`, `tools` — `dataset_context` 등은 enrich 자동 추가.
선택 입력 `description`: 사용자가 입력한 보고서 부가 설명 — plan 설계·태스크 instruction 에 반영.

Plan 은 **무엇을 / 어떤 선행 이후에** 만 기술. key 이름·layout·런타임 클래스·문서 composition 은 plan 에 넣지 않는다.

## root

| 필드 | 설명 |
|------|------|
| `plan_id` | `pl-{slug}-{uuid8}` |
| `title`, `description` | 보고서 제목·한 줄 요약 |
| `data_id` | 입력 did |
| `tools` | MCP tool_path 배열 (catalog) |
| `tasks[]` | DAG 노드 (**배열 순서 ≠ 실행 순서**) |

## tasks[]

| 필드 | 설명 |
|------|------|
| `task_id` | `task-{kebab}-{uuid8}` |
| `type` | `data` \| `analyze` \| `visual` \| `narrative` \| `release` **만** |
| `title`, `description` | 제목·30자 부제 |
| `instruction` | 실행 LLM 에 전달할 미션 |
| `context` | upstream task_id[] (DAG edge) |
| `tools` | *(선택)* plan.tools 부분집합 — MCP 쓰는 태스크만 |

## type · DAG

| type | 용도 | context (DAG 실행 순서) |
|------|------|-------------------------|
| `data` | 로드·갱신·원본 데이터 준비 | `[]` root |
| `analyze` | 집계·EDA | data 등 upstream |
| `visual` | chart/table | analyze 등 (순서만; **데이터는 칠판 전체**) |
| `narrative` | ReportDocument 초안 | analyze + visual |
| `release` | QA·출판 `report` | **narrative + 모든 visual + narrative 선행 analyze** |

- `context` → **실행 순서(DAG edge)**. codegen 시 `upstream_context` 칠판에는 **현재까지 완료된 모든 태스크** key 가 포함됨.
- raw row downstream 전달 설계 금지
- plan 루트에 `layout` 필드 금지

## tools 할당

| type | tasks[].tools |
|------|---------------|
| `data` | MCP 갱신 시 지정 — **파일 소스만 데이터셋이면 `[]` 가능** (Pangea parquet 로드) |
| `analyze` | 재조회·추가 MCP 시만 |
| `visual` / `narrative` / `release` | 보통 `[]` |

## instruction 작성

1. 데이터 출처 — data_id vs context upstream (title 로 지칭)
2. 산출 성격 — 통계/chart/문단 등 (key 이름 생략 가능).
   - **analyze**: 질문에 필요한 파생(모집단·순위·상위/하위·기준선). 합계만 금지.
   - **visual**: 질문에 맞는 차트 종류. 서브플롯·다중 grid 금지. 한글 헤더.
   - **narrative**: 요약(고유명+숫자)·표/차트 해석·결론. 「초안 조립」만 쓰지 말 것.
   - **release**: junk·placeholder·수치 불일치만 patch 후 출판. 한글 본문 재작성 금지.
3. raw 금지 — 집계·요약만
4. title·description 은 **일반 한글** — 내부 용어·영문 암호 사용 금지

# 출력 (JSON Only)

```json
{
  "plan_id": "pl-regional-sales-a1b2c3d4",
  "title": "지역별 매출 분석",
  "description": "업로드 매출 데이터 집계·시각화",
  "data_id": "did-sales-regional-e5f6a7b8",
  "tools": [],
  "tasks": [
    {
      "task_id": "task-load-data-e1a2b3c4",
      "type": "data",
      "title": "매출 데이터 로드",
      "description": "로드·갱신",
      "tools": [],
      "instruction": "data_id 로드 후 분석 대상 행 선정, 집계용 메타를 TaskContext에 저장. raw row 금지.",
      "context": []
    },
    {
      "task_id": "task-aggregate-f2b3c4d5",
      "type": "analyze",
      "title": "지역별 집계",
      "description": "기술통계",
      "instruction": "로드 데이터로 지역별 매출·비중·순위를 집계해 TaskContext에 저장. 합계만 금지.",
      "context": ["task-load-data-e1a2b3c4"]
    },
    {
      "task_id": "task-chart-a3b4c5d6",
      "type": "visual",
      "title": "지역 매출 차트",
      "description": "비교 차트",
      "instruction": "집계로 지역 비교 차트와 한글 헤더 표를 저장. 차트 타입은 비교에 맞게. 다중 grid 금지.",
      "context": ["task-aggregate-f2b3c4d5"]
    },
    {
      "task_id": "task-narrative-d4e5f6a7",
      "type": "narrative",
      "title": "분석 보고서 초안",
      "description": "ReportDocument",
      "instruction": "모집단과 핵심 발견이 있는 요약, 표/차트 해석, 결론을 포함한 초안. 표+차트만 두지 말 것.",
      "context": ["task-aggregate-f2b3c4d5", "task-chart-a3b4c5d6"]
    },
    {
      "task_id": "task-release-c5e6f7a8",
      "type": "release",
      "title": "최종 검토·출판",
      "description": "QA",
      "instruction": "첨부 report_document 검토 후 junk·placeholder·수치 불일치만 patch 하고 출판. 한글 본문 재작성 금지.",
      "context": [
        "task-narrative-d4e5f6a7",
        "task-chart-a3b4c5d6",
        "task-aggregate-f2b3c4d5",
        "task-load-data-e1a2b3c4"
      ]
    }
  ]
}
```

## 금지

- type 에 `profile`, `chart`, `report`, `review` 등 사용
- plan JSON 에 PangeaExDataFrame·TaskContext·MCP name 포함
- title·instruction 에 업계 내부 암호·영문 관례어 — 사용자·실행 LLM 이 이해하는 한글 title 사용
