# Node (NodeV)

**Node**는 SAG-E에서 LLM 호출 시 입·출력을 Pydantic으로 고정하고, 검증 실패 시 재시도·학습(`validated.md`)까지 수행하는 실행 단위입니다.

호출 관계: **API → Node (`nodes[...].run`) → MCP Tool (`sage.mcp.call`)**

> Node.js의 Node와 무관합니다.

---

## 디렉터리 구조

```
nodes/
├── data/
│   └── pangeaze/           # 멀티 소스 → schema/adapter/unify codegen
├── report/
│   ├── plan/               # ReportPlanOutput (DAG)
│   └── task/
│       ├── data/           # type: data
│       ├── analyze/        # type: analyze
│       ├── visual/         # type: visual
│       ├── narrative/      # type: narrative
│       └── release/        # type: release
├── tool/
│   ├── generator/          # ToolPack codegen
│   ├── executor/           # NL → caller codegen
│   └── update/             # 도구 수정
└── test/                   # NodeV 동작 확인용
```

각 노드 폴더:

| 파일 | 역할 |
|------|------|
| `instruction.md` | LLM system 프롬프트 (규칙·금지사항·예시) |
| `validated.md` | 재시도 중 축적된 lesson — 다음 codegen에 주입 |
| `main.py` | `@node` + `NodeV` (또는 `TaskCodegenNode`) 클래스 |

`nodes/report/legacy/` 는 이전 plan/task 스키마용 — **신규 개발 시 사용하지 않습니다.**

---

## NodeV 기본 패턴

```python
from pydantic import BaseModel, Field
from sage.nodes import node, NodeV


class Query(BaseModel):
    query: str = Field(description="사용자 질의")


class Result(BaseModel):
    answer: float


@node(input=Query, output=Result)
class Test(NodeV):
    pass
```

- `@node` — 입·출력 Pydantic 모델 등록
- `NodeV.run(**kwargs)` — LLM codegen 루프 (최대 `max_retries`, 기본 3)
- `LLMFactory.DEFAULT_LLM_TYPE` (`SAGE_LLM_TYPE`) 로 백엔드 선택
- Gemini/Cursor — structured output (`response_model`)

### 실행 예

```python
import asyncio
from sage.nodes import nodes

async def main():
    res = await nodes["test"].run(query="배열 평균, ex. 3, 5, 1")
    print(res)  # Result(answer=3.0)

asyncio.run(main())
```

노드 키는 `nodes/{path}` — 슬래시 구분 (`report/plan`, `data/pangeaze`).

---

## codegen 루프 (NodeV.run)

1. 입력 Pydantic 검증
2. `instruction.md` + `validated.md` + 입력 프롬프트 조합
3. LLM `generate_async` → raw JSON/text
4. 출력 Pydantic + 커스텀 Validator 검증
5. 실패 시 에러 피드백 + **전체 재생성** (attempt ≤ max_retries)
6. 성공 시 `validated.md`에 lesson flush (옵션: `_lesson_flush=False`)

### lesson 학습

| 메서드 | 설명 |
|--------|------|
| `note_failure(category, error_msg)` | 재시도 중 실패 축적 (즉시 파일 쓰기 X) |
| `flush_learned_lessons(resolved=True)` | 성공/실패 후 `validated.md`에 구조화 lesson 저장 |
| `record_immediate_lesson(...)` | post_validate 등 즉시 기록 |

report runner의 `codegen_task`는 태스크별 `get_task_node(type)` NodeV를 사용합니다.

---

## Report 태스크 노드 (TaskCodegenNode)

Plan의 `type`별 codegen 노드:

| type | 노드 경로 | 역할 |
|------|-----------|------|
| `data` | `report/task/data` | Pangea 로드·MCP 갱신·원본 데이터 |
| `analyze` | `report/task/analyze` | upstream JSON 집계·통계 |
| `visual` | `report/task/visual` | 차트·표 데이터 |
| `narrative` | `report/task/narrative` | 서술형 초안 |
| `release` | `report/task/release` | layout·report.json 조립 |

공통 출력: `TaskOutput` (`code` — `run_task(run, ctx)` 함수 포함 Python 소스)

Plan 출력: `ReportPlanOutput`

```python
class PlanTask(BaseModel):
    task_id: str          # task-{kebab}-{uuid8}
    type: TaskType        # data | analyze | visual | narrative | release
    title: str
    description: str      # 30자 이내
    instruction: str      # codegen 미션
    context: list[str]    # upstream task_id (DAG)
    tools: list[str]      # MCP path
```

---

## 커스텀 Validator

```python
from sage.nodes import node, NodeV, BaseValidator

class MyValidator(BaseValidator):
    async def validate(self, output, **kwargs):
        if ...:
            raise ValueError("규칙 위반")

@node(input=..., output=...)
class Plan(NodeV):
    def __init__(self):
        super().__init__(validators=[MyValidator()])
```

`report/plan`은 `PlanStructureValidator`로 DAG·task_id 형식을 검증합니다.

---

## Self-Healing (도구)

| 클래스 | 용도 |
|--------|------|
| `ToolFix` | `execute_with_fix` — 도구 main/caller 수정 |
| `SourceFix` | 태스크 소스·caller 문법 수정 |

---

## 새 노드 추가

1. `nodes/{domain}/{name}/` 생성
2. `instruction.md` 작성 (출력 JSON 스키마·금지 규칙 명시)
3. `main.py` — `@node(input=X, output=Y)` + `NodeV` 서브클래스
4. (선택) `validated.md` — 초기 lesson 또는 빈 파일
5. `sage.nodes.factory`가 `nodes/` 트리를 스캔 — 별도 등록 불필요

환경 변수 `SAGE_NODES_PATH`로 노드 루트를 변경할 수 있습니다 ([cfg.py](../cfg.py)).

---

## 관련 코드

| 모듈 | 설명 |
|------|------|
| `sage/nodes/framework.py` | NodeV, `@node`, codegen 루프 |
| `sage/nodes/factory.py` | `nodes["report/plan"]` 카탈로그 |
| `sage/report/task_codegen.py` | TaskCodegenNode 베이스 |
| `sage/report/runner.py` | `codegen_task`, `iter_plan_tasks` |

API·SSE 흐름: [docs.md](docs.md)
