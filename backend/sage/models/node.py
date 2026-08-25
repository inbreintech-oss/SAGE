"""노드 입출력 모델 (~Input / ~Output)."""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TaskType = Literal["data", "analyze", "visual", "narrative", "release"]


# --- legacy plan / task ---

class LayoutItem(BaseModel):
    row: int = Field(..., ge=0, description="행 인덱스 (0부터 시작)")
    col: int = Field(..., ge=0, description="열 인덱스 (0부터 시작)")
    task_id: str = Field(..., pattern=r"^task-", description="연결될 활동 식별자")
    span: int = Field(..., ge=1, le=10, description="그리드 너비 (1~10)")


class LegacyPlanTask(BaseModel):
    """레거시 ToDoList 태스크 항목."""

    task_id: str = Field(..., description="해당 작업 ID (예: task-{name as Kebabcase}-{uuid})")
    title: str = Field(..., description="단계별 제목")
    description: Optional[str] | None = Field(None, description="작업 세부 설명")
    instruction: str = Field(..., description="이 단계에서 수행할 상세 분석 지침")
    context: List[str] = Field(default_factory=list, description="참조할 이전 작업 ID 목록")
    tools: List[str] = Field(default_factory=list, description="활용 가능한 도구 목록")


class ToDoListOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plan_id: str = Field(..., description="플랜 고유 ID")
    title: str = Field(..., description="리포트 전체 제목")
    layout: List[LayoutItem] = Field(..., description="리포트 레이아웃 (행 단위 구성)")
    tasks: List[LegacyPlanTask] = Field(..., description="상세 분석 작업 리스트")
    tools: List[str] = Field(default_factory=list, description="사용될 MCP 도구 경로 리스트")


# 하위 호환 alias
ToDoList = ToDoListOutput
Task = LegacyPlanTask


class TaskInput(BaseModel):
    """Task 실행 노드 입력."""

    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(..., description="해당 작업 ID (예: task-{name as Kebabcase}-{uuid8})")
    data: str = Field(description="작업에서 사용될 분석 대상 데이터")
    title: str = Field(..., description="단계 제목")
    description: Optional[str] | None = Field(None, description="작업 세부 설명")
    prompt: str = Field(..., description="분석 미션 지침")
    tools: List[str] = Field(default_factory=list, description="작업 내 활용 가능한 MCP 도구 목록")
    context: Dict[str, Any] = Field(default_factory=dict, description="작업 구성 시 참고할 이전 단계 결과 목록")


class TaskUpdateInput(BaseModel):
    """작업 업데이트 노드 입력."""

    query: str = Field(description="사용자 질의/요청 사항")
    plan: Dict[str, Any] = Field(description="보고서 작성 시 사용된 전체 구성 데이터")
    task: TaskInput = Field(description="업데이트 대상 작업 정보")
    code: str = Field(description="작업 내 사용된 분석 로직 또는 파이썬 소스 코드")


# 하위 호환 alias
TaskUpdate = TaskUpdateInput


class UserQueryInput(BaseModel):
    query: str = Field(description="사용자 질의/요청 사항")
    tools: List[str] | None = Field(None, description="이미 구성되어 제공 가능한 도구 정보, 사용(호출)만 하라")


UserQuery = UserQueryInput


class DataQueryInput(UserQueryInput):
    data: str = Field(description="분석 대상 데이터(리소스) 구성")


DataQuery = DataQueryInput


class SourceErrInput(BaseModel):
    code: str = Field(description="에러가 발생한 파이썬 소스 코드")
    error: str | None = Field(None, description="발생한 트레이스백 또는 에러 메시지")


SourceErr = SourceErrInput


class SourceFixedOutput(BaseModel):
    fixed_code: str = Field(..., description="교정된 새로운 파이썬 소스 코드")
    explanation: Optional[str] = Field(None, description="수정 내용에 대한 설명")


SourceFixed = SourceFixedOutput


# --- data 노드 ---

class SourceMetadataBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(..., description="소스 식별자 (예: src-a1b2c3d4)")
    description: Optional[str] = Field(None, description="소스에 대한 설명")


class FileSourceMetadata(SourceMetadataBase):
    source_type: Literal["file"] = "file"
    path: str = Field(description="원천 파일 소스 패스(파일명)")
    columns: List[str] = Field(..., description="로드된(selected) 데이터프레임 컬럼 리스트")
    column_defs: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="파일 전체 컬럼 정의(name, type, selected). columns 는 selected=true 로 로드된 컬럼만.",
    )
    column_types: Optional[Dict[str, str]] = Field(None, description="컬럼별 데이터 타입")
    sample_data: Optional[List[Dict[str, Any]]] = Field(None, description="데이터 샘플 (최대 3개)")
    file_format: str = Field(default="csv", description="파일 형식 (csv, xlsx 등)")


class ToolSourceMetadata(SourceMetadataBase):
    source_type: Literal["tool"] = "tool"
    tool_path: str = Field(..., description="도구 호출 경로 (서버명/도구명)")
    tool_spec: Dict[str, Any] | List = Field(..., description="JSON 명세")


class DBSourceMetadata(SourceMetadataBase):
    source_type: Literal["db"] = "db"
    connection: str = Field(..., description="대상 DB 연결 식별자")
    columns: List[str] = Field(..., description="조회될 테이블/쿼리의 컬럼 리스트")
    query: Optional[str] = Field(None, description="실행될 SQL 쿼리")


SourceMetadata = Annotated[
    Union[FileSourceMetadata, ToolSourceMetadata, DBSourceMetadata],
    Field(discriminator="source_type"),
]


class DataAnalysisInput(BaseModel):
    dataset_name: str
    user_query: Optional[str] = ""
    sources: List[SourceMetadata] = Field(..., description="데이터 소스 리스트")
    confirmed_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="pangeaze/update 시 UI 확정 JSON 스키마 — 있으면 schema/unify 가 이를 준수",
    )


class MergeStrategy(BaseModel):
    left_source: str
    right_source: str
    how: str = Field(description="inner, left, right, outer")
    on: List[str] = Field(description="병합 기준 컬럼 목록")


class DataAnalysisOutput(BaseModel):
    schema_code: str = Field(description="schema.py에 저장될 Pydantic 클래스 코드")
    unify_logic_code: str = Field(description="unify.py에 저장될 데이터 전처리 및 병합 파이썬 코드")
    column_mapping: Dict[str, str] = Field(description="원본 소스.컬럼명과 표준화된 컬럼명 매핑")
    merge_strategies: List[MergeStrategy]

    @field_validator("unify_logic_code")
    @classmethod
    def _unify_contract(cls, v: str) -> str:
        from sage.data.unify_contract import validate_unify_logic_code

        validate_unify_logic_code(v)
        return v


class DataExecutionInput(BaseModel):
    confirmed_schema: Dict[str, Any] = Field(..., description="사용자가 UI에서 최종 확정한 JSON 스키마")
    sources: List[SourceMetadata]


class PangeaOutput(BaseModel):
    metadata: Dict[str, Any] = Field(description="metadata.json 설정 데이터")
    schema_code: str = Field(..., description="데이터 검증을 위한 schema.py 파이썬 소스 코드")
    adapter: str = Field(..., description="데이터 변환을 위한 adapter.py 파이썬 소스 코드")
    unify_logic_code: str = Field(description="데이터 초벌 구축을 위한 unify.py 파이썬 소스 코드")
    suggested_queries: List[str] = Field(
        default_factory=list,
        description="통합 데이터셋 기반 추천 분석 질의 (3~5개, 한국어)",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("unify_logic_code")
    @classmethod
    def _unify_contract(cls, v: str) -> str:
        from sage.data.unify_contract import validate_unify_logic_code

        validate_unify_logic_code(v)
        return v


# --- report plan 노드 ---

class ReportPlanInput(BaseModel):
    data_id: str = Field(..., description="분석 대상 dataset id (did)")
    query: str = Field(..., description="보고서 작성 요청·질의")
    description: Optional[str] = Field(None, description="사용자가 입력한 보고서 부가 설명")
    tools: List[str] = Field(
        default_factory=list,
        description="MCP tools spec (enrich) — call() 은 spec name·tool_path·input 만 사용",
    )


class PlanTask(BaseModel):
    task_id: str = Field(..., pattern=r"^task-", description="task-{kebab-name}-{uuid8}")
    type: TaskType = Field(..., description="태스크 유형 (data/analyze/visual/narrative/release)")
    title: str = Field(..., description="작업 제목")
    description: str = Field(..., max_length=30, description="30자 이내 부제")
    instruction: str = Field(..., description="실행 LLM/코드 생성기에 전달할 상세 지시")
    context: List[str] = Field(default_factory=list, description="upstream task_id 목록 (DAG edge)")
    tools: List[str] = Field(
        default_factory=list,
        description="이 태스크 codegen 에 전달할 MCP tool path",
    )


class ReportPlanOutput(BaseModel):
    plan_id: str = Field(..., pattern=r"^pl-", description="pl-{slug}-{uuid8}")
    title: str = Field(..., description="보고서 제목")
    description: str = Field(..., description="플랜 목표 한 줄 요약")
    data_id: str = Field(..., description="분석 대상 dataset id")
    tools: List[str] = Field(default_factory=list, description="plan 전체 MCP tool path catalog")
    tasks: List[PlanTask] = Field(..., min_length=1, description="태스크 DAG 노드 목록")


# --- report task 노드 ---

class TaskRun(BaseModel):
    """단일 태스크 실행 스펙 — plan 루트 + plan.tasks[] 항목 통합."""

    plan_id: str = Field(..., pattern=r"^pl-")
    data_id: str = Field(..., description="분석 대상 dataset id (did)")
    plan_title: str = Field(default="", description="보고서 제목 (narrative/release 등)")
    task_id: str = Field(..., pattern=r"^task-")
    type: TaskType
    title: str
    description: str = Field(default="", max_length=30)
    instruction: str
    context: List[str] = Field(default_factory=list, description="upstream task_id 목록")

    @classmethod
    def from_plan(
        cls,
        plan: Union[ReportPlanOutput, dict],
        task: Union[PlanTask, dict],
    ) -> TaskRun:
        if isinstance(plan, dict):
            plan_id = plan["plan_id"]
            data_id = plan["data_id"]
            plan_title = plan.get("title", "")
        else:
            plan_id = plan.plan_id
            data_id = plan.data_id
            plan_title = plan.title

        if isinstance(task, dict):
            return cls(
                plan_id=plan_id,
                data_id=data_id,
                plan_title=plan_title,
                task_id=task["task_id"],
                type=task["type"],
                title=task["title"],
                description=task.get("description") or "",
                instruction=task["instruction"],
                context=list(task.get("context") or []),
            )

        return cls(
            plan_id=plan_id,
            data_id=data_id,
            plan_title=plan_title,
            task_id=task.task_id,
            type=task.type,
            title=task.title,
            description=task.description or "",
            instruction=task.instruction,
            context=list(task.context),
        )


class TaskCodegenInput(BaseModel):
    plan_id: str = Field(..., pattern=r"^pl-", description="plan_id")
    data_id: str = Field(..., description="분석 대상 dataset id (did)")
    task_id: str = Field(..., pattern=r"^task-", description="task_id")
    type: TaskType = Field(..., description="태스크 유형")
    title: str = Field(..., description="태스크 제목")
    description: str = Field(default="", description="태스크 부제 (30자 이내)")
    instruction: str = Field(..., description="plan.tasks[].instruction — 이 태스크 미션")
    context: List[str] = Field(default_factory=list, description="upstream task_id 목록")
    rid: str | None = Field(default=None, pattern=r"^rp-", description="보고서 id")
    plan_task_ids: List[str] = Field(
        default_factory=list,
        description="plan.tasks[].task_id — stale context·llm_attach 필터",
    )
    tools: List[str] = Field(default_factory=list, description="MCP tools spec (enrich)")
    user_description: str | None = Field(
        None, description="사용자 부가 설명 (req.description) — domain brief inject 조건"
    )
    report_query: str | None = Field(None, description="보고서 query — domain brief inject 조건")


class TaskOutput(BaseModel):
    task_id: str = Field(..., pattern=r"^task-", description="plan.tasks[].task_id")
    title: str = Field(..., description="태스크 제목")
    description: str = Field(default="", description="executor 역할·산출 key 요약")
    code: str = Field(
        ...,
        min_length=1,
        description="async def run_task(task: TaskRun, ctx: TaskContext, reporter=None) Python 모듈 전체",
        json_schema_extra={"validation": "tool"},
    )

    @model_validator(mode="after")
    def check_source_nonempty(self):
        if not self.code.strip():
            raise ValueError("source 는 비어 있을 수 없습니다.")
        return self
