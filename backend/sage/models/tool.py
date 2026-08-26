"""Tool 노드 입출력 모델 (~Input / ~Output)."""

from typing import List, Optional, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ToolGenerateInput(BaseModel):
    """도구 생성 노드 입력."""

    query: str = Field(description="생성하고자 하는 도구의 기능 정의 또는 분석 질의")
    ref_code: str | None = Field(default=None, description="참고할 도구 소스 코드")
    tools: List[str] | None = Field(default=None, description="참고할 MCP 도구 경로 목록 (예: yf/fx-rate)")
    description: str | None = Field(default=None, description="도구 설명")
    secret_id: str | None = Field(
        default=None,
        description="SecretKey secret_id (sk-*) — 등록된 keys[] 를 codegen 프롬프트에 포함",
    )
    keys: List[str] | None = Field(
        default=None,
        description="secret_id 에서 해석된 key_name 목록 (API 입력 아님 — 내부 자동 채움)",
    )
    provider: str | None = Field(
        default=None,
        description="secret_id 에서 조회된 provider (API 입력 아님 — 내부 자동 채움)",
    )
    user_id: str = Field(default="admin", description="SecretKey 조회 user_id")

    @field_validator("keys")
    @classmethod
    def _normalize_keys(cls, v: List[str] | None) -> List[str] | None:
        if not v:
            return v
        return [str(k).strip().upper() for k in v if k and str(k).strip()]

    @classmethod
    async def from_request(
        cls,
        *,
        query: str,
        tools: List[str] | None = None,
        description: str | None = None,
        ref_code: str | None = None,
        secret_id: str | None = None,
        user_id: str = "admin",
    ) -> "ToolGenerateInput":
        from sage.secret.keys import prepare_tool_secret_fields

        resolved_secret_id, provider, keys = await prepare_tool_secret_fields(
            user_id=user_id,
            secret_id=secret_id,
            query=query,
        )
        return cls(
            query=query,
            tools=tools,
            description=description,
            ref_code=ref_code,
            secret_id=resolved_secret_id,
            provider=provider,
            keys=keys,
            user_id=user_id,
        )


class ToolPackCodegen(BaseModel):
    """도구 생성 노드 LLM 출력 — code·메타·호출 예시 (caller 제외)."""

    tool_id: str = Field(description="MCP 도구 식별자 (tm-{name}-{uuid8}, 소문자·하이픈)")
    title: str = Field(description="도구 명칭")
    description: str = Field(description="이 도구의 역할 및 반환 데이터 구조에 대한 설명")
    code: str = Field(
        ...,
        min_length=1,
        description="MCP 도구 파이썬 소스 — @mcp.tool 함수와 Pydantic 입출력 모델 포함",
        json_schema_extra={"validation": "tool"},
    )
    query_examples: List[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="사용자에게 제시할, 이 도구를 호출하기 위한 자연어 문장 예제 3개",
    )

    @field_validator("query_examples")
    @classmethod
    def _non_empty_examples(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if len(cleaned) != 3:
            raise ValueError("query_examples 는 비어 있지 않은 문장 3개여야 합니다.")
        return cleaned


class ToolPack(BaseModel):
    """MCP 도구 정의 — executor code + 테스트 caller + 호출 예시."""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    tool_id: str = Field(description="MCP 도구 식별자 이름(소문자, - 만 사용)")
    title: str = Field(description="도구 명칭")
    description: str | None = Field(default=None, description="이 도구의 역할 및 반환 데이터 구조에 대한 설명")
    code: str | None = Field(
        default=None,
        description="MCP 도구 파이썬 소스, Pydantic 모델을 반환하는 함수가 포함되어 있어야 함",
        json_schema_extra={"validation": "tool"},
    )
    caller: str | None = Field(
        default=None,
        description="생성된 tool 함수를 호출하는 smoke 테스트용 파이썬 실행 코드",
        json_schema_extra={"validation": "tool"},
    )
    query_examples: List[str] = Field(
        default_factory=list,
        max_length=3,
        description="사용자에게 제시할, 이 도구를 호출하기 위한 자연어 문장 예제 3개",
    )

    @field_validator("query_examples")
    @classmethod
    def _validate_examples(cls, v: List[str]) -> List[str]:
        if not v:
            return v
        cleaned = [s.strip() for s in v if s and s.strip()]
        if len(cleaned) != 3:
            raise ValueError("query_examples 가 제공되면 비어 있지 않은 문장 3개여야 합니다.")
        return cleaned

    @model_validator(mode="after")
    def check_at_least_one_exists(self) -> Self:
        if self.code is None and self.caller is None:
            raise ValueError("code와 caller가 동시에 None일 수 없습니다. 최소 하나는 제공되어야 합니다.")
        return self


class ToolCallSummary(BaseModel):
    tool_id: str = Field(..., description="실행할 도구의 고유 ID")
    args: dict = Field(default_factory=dict, description="도구 함수에 전달할 인자값들")
    thought: Optional[str] = Field(None, description="LLM이 이 도구를 선택한 이유 또는 추론 과정")

    model_config = ConfigDict(from_attributes=True)


class ToolExecOutput(BaseModel):
    caller: str = Field(
        json_schema_extra={"validation": "tool"},
        description="질의를 만족하는 caller.py. 도구 원응답을 무조건 그대로 반환하지 말 것",
    )
    summary: ToolCallSummary = Field(description="도구 호출을 위한 메타데이터 및 인자 정보")

    model_config = ConfigDict(from_attributes=True)


# 하위 호환 alias
ToolExecResult = ToolExecOutput


class ToolUpdateInput(BaseModel):
    """ToolUpdate 노드 입력."""

    query: str = Field(description="사용자의 수정 요청 사항 (Instruction)")
    ref_code: str | None = Field(default=None, description="참고할 도구 소스 코드")
    tool_id: str = Field(description="수정 대상 도구 식별자")
    tool: ToolPack = Field(description="기존 도구 데이터 및 소스")
    secret_id: str | None = Field(default=None, description="SecretKey secret_id (sk-*)")
    provider: str | None = Field(default=None, description="secret_id 에서 조회된 provider (내부 자동 채움)")
    keys: List[str] | None = Field(default=None, description="secret_id keys (내부 자동 채움)")
    user_id: str = Field(default="admin", description="SecretKey 조회 user_id")

    model_config = ConfigDict(from_attributes=True)


class ToolErr(BaseModel):
    error: str = Field(None, description="실행 오류 — 이것을 고친다. 원본 복붙 금지")
    tool: ToolPack = Field(description="수정전 도구 소스 코드")
    fix: str = Field("all", description="수정 대상 'all|caller'")
