import json
import uuid
from datetime import datetime
from typing import List, Optional, Any, Dict, Literal, Annotated

from pydantic import BaseModel, Field, ConfigDict, BeforeValidator, AfterValidator

from sage.models.node import LayoutItem as NodeLayoutItem
from sage.models.tool import ToolPack

# 공통 타입 정의
ReportStatus = Literal[
    "initializing",
    "planned",
    "completed",
    "failed",
    "assetized",
    "executed",
    "published",
]
ToolStatus = Literal["syntax-passed", "failed", "assetized", "generated"]
TargetType = Literal["task", "tool"]


def has_nested_list(data: Any) -> bool:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, list):
                return True
            if has_nested_list(item):
                return True
    elif isinstance(data, dict):
        for value in data.values():
            if has_nested_list(value):
                return True
    return False


def validate_mongo_nested_array(v: Any) -> Any:
    if has_nested_list(v):
        try:
            return json.dumps(v, ensure_ascii=False)
        except (TypeError, ValueError):
            return v
    return v


def auto_load_json(v: Any) -> Any:
    if isinstance(v, str):
        try:
            if v.startswith(("{", "[")):
                return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            pass
    return v


MongoSafeField = Annotated[Any, BeforeValidator(validate_mongo_nested_array), AfterValidator(auto_load_json)]


class Report(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rid: str = Field(pattern=r"^rp-", description="보고서 고유 식별자 (rp- 접두어)")
    session_id: str = Field(pattern=r"^sess-", description="연결된 세션 고유 식별자 (sess- 접두어)")
    did: str = Field(pattern=r"^did-", description="데이터셋 식별자")
    plan_id: Optional[str] = Field(None, pattern=r"^pl-", description="현재 보고서에서 활성화된 플랜 식별자")
    title: str = Field(description="보고서의 최종 제목")
    status: ReportStatus = Field("initializing", description="보고서의 현재 생성/실행 단계 상태")
    query: str = Field(description="사용자가 입력한 원본 질문 또는 요청사항")
    description: Optional[str] = Field(None, description="사용자가 입력한 보고서 부가 설명")
    tools: List[str] = Field(default_factory=list, description="생성 요청 시 지정한 도구 식별자(path) 목록")
    version: int = Field(1, description="보고서의 수정 및 갱신 버전 번호")
    created_at: datetime = Field(default_factory=datetime.now, description="보고서 최초 생성 일시")
    updated_at: datetime = Field(default_factory=datetime.now, description="보고서 정보 최종 수정 일시")


class LayoutItem(NodeLayoutItem):
    model_config = ConfigDict(from_attributes=True)


class Plan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: str = Field(pattern=r"^pl-", description="플랜 고유 식별자 (pl- 접두어)")
    rid: str = Field(pattern=r"^rp-", description="참조하는 보고서 고유 식별자")
    session_id: str = Field(pattern=r"^sess-", description="연결된 세션 고유 식별자")
    title: str = Field(description="보고서 생성을 위한 전략적 설계 명칭")
    blueprint: Dict[str, Any] = Field(
        default_factory=dict,
        description="태스크 간의 데이터 흐름, 로직 및 상세 실행 시나리오 명세",
    )
    tools: List[str] = Field(default_factory=list, description="이 플랜 전반에서 공용으로 사용될 도구 목록")
    created_at: datetime = Field(default_factory=datetime.now, description="플랜 설계 및 확정 일시")


class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str = Field(pattern=r"^task-", description="태스크 고유 식별자 (task- 접두어)")
    rid: str = Field(pattern=r"^rp-", description="참조하는 보고서 고유 식별자")
    plan_id: str = Field(pattern=r"^pl-", description="소속된 플랜 고유 식별자")
    session_id: str = Field(pattern=r"^sess-", description="연결된 세션 고유 식별자")
    tool_id: str = Field(pattern=r"^tm-", description="이 태스크 수행을 위해 호출할 도구 식별자")
    title: str = Field(description="작업 명칭")
    description: Optional[str] = Field(None, description="작업에 대한 세부/추가 설명")
    context: List[str] = Field(
        default_factory=list,
        description="이 태스크 실행을 위해 선행되어야 하거나 참조해야 하는 태스크 ID 목록",
    )
    tools: List[str] = Field(
        default_factory=list,
        description="이 단계의 작업 범위 내에서 국한되어 사용되는 추가 도구 목록",
    )
    updated_at: datetime = Field(default_factory=datetime.now, description="태스크 상태 및 정보 최종 변경 일시")


class Tool(ToolPack):
    """MongoDB 도구 ORM — ToolPack + API/DB 메타."""

    model_config = ConfigDict(from_attributes=True)

    category: str | None = Field(None, description="도구 카테고리")
    tags: List[str] | None = Field(None, description="도구 태그")
    query: str | None = Field(None, description="도구 생성/수정 시 사용자 질의")
    secret_id: str | None = Field(None, description="도구 키 SecretKey secret_id (sk-*)")
    status: ToolStatus = Field(default="syntax-passed", description="도구 상태 (assetized 시 MCP HTTP 노출)")
    created_at: datetime = Field(default_factory=datetime.now, description="도구 최초 등록 일시")
    updated_at: datetime = Field(default_factory=datetime.now, description="도구 정의 최종 수정 일시")


class KeyItem(BaseModel):
    key_name: str = Field(description="키 이름 (대문자 저장)")
    key_value: str = Field(description="키 값")


class SecretKey(BaseModel):
    """API Key 등 민감 정보 — MongoDB secrets 컬렉션."""

    model_config = ConfigDict(from_attributes=True)

    secret_id: str = Field(description="sk-{uuid.uuid4().hex}")
    user_id: str = Field(default="admin", description="키 소유 사용자")
    provider: str = Field(description="제공업체나 기관")
    keys: List[KeyItem] = Field(description="키 목록")
    description: str = Field(default="", description="키 용도 설명")
    created_at: datetime = Field(default_factory=datetime.now, description="등록 일시")
    updated_at: datetime = Field(default_factory=datetime.now, description="수정 일시")

    @classmethod
    def make_id(cls) -> str:
        """랜덤 UUID 기반의 고유 secret_id 생성"""
        return f"sk-{uuid.uuid4().hex}"


class Execution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exec_id: str = Field(pattern=r"^exec-", description="실행 기록 식별자 (exec- 접두어)")
    target_type: TargetType = Field(description="실행 주체 유형 (태스크 또는 도구)")
    target_id: str = Field(description="실행된 대상의 ID (task_id 또는 tool_id)")
    session_id: Optional[str] = Field(None, pattern=r"^sess-", description="실행 당시의 세션 식별자")
    rid: str = Field(pattern=r"^rp-", description="연관된 보고서 식별자")
    result: MongoSafeField | None = Field(None, description="실행 성공 시 반환된 결과 데이터 세트")
    is_success: bool = Field(True, description="실행 성공 여부 플래그")
    error_msg: Optional[str] = Field(None, description="실행 실패 시 기록되는 오류 원인 및 메시지")
    runtime_ms: Optional[int] = Field(None, description="실행 시작부터 종료까지 걸린 시간 (ms)")
    executed_at: datetime = Field(default_factory=datetime.now, description="실행이 완료된 기록 시각")


class Log(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: str = Field(pattern=r"^log-", description="로그 고유 식별자 (log- 접두어)")
    rid: Optional[str] = Field(None, description="해당 로그와 연관된 보고서 ID")
    session_id: Optional[str] = Field(None, description="해당 로그와 연관된 세션 ID")
    level: str = Field("INFO", description="로그 중요도 레벨 (INFO, DEBUG, WARNING, ERROR)")
    msg: str = Field(description="로그 내용 전문")
    extra: Dict[str, Any] = Field(default_factory=dict, description="로그 분석을 위한 추가적인 메타데이터")
    timestamp: datetime = Field(default_factory=datetime.now, description="로그 발생 시각")


class ChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str = Field(description="메시지 발신자 역할 (user, assistant, system)")
    content: str = Field(description="전달된 메시지 텍스트 내용")
    rid: Optional[str] = Field(None, pattern=r"^rp-", description="해당 대화의 결과로 생성되거나 갱신된 보고서 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="메시지 전송 및 수신 시각")


class Session(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(pattern=r"^sess-", description="세션 고유 식별자 (sess- 접두어)")
    user_id: Optional[str] = Field(None, description="세션을 소유한 사용자의 고유 식별자")
    title_query: str = Field(description="세션을 대표하는 최초의 질의 또는 요약된 주제")
    chat_logs: List[ChatMessage] = Field(default_factory=list, description="현재 세션에서 발생한 모든 채팅 메시지 목록")
    report_stack: List[str] = Field(default_factory=list, description="이 세션에서 생성된 리포트 ID들의 생성 순서 목록")
    current_rid: Optional[str] = Field(None, description="사용자가 현재 화면에 띄워놓은 리포트 식별자")
    updated_at: datetime = Field(default_factory=datetime.now, description="세션 정보가 마지막으로 갱신된 시각")
