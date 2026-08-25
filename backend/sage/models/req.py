"""API 요청/응답 모델 (~Request 규격)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sage.models.doc import KeyItem


# --- tool API ---

class ToolGenerateRequest(BaseModel):
    """도구 생성 요청."""

    query: str = Field(description="생성하고자 하는 도구의 기능 정의 또는 분석 질의")
    ref_code: str | None = Field(None, description="참고할 도구 소스 코드")

    tools: List[str] | None = Field(None, description="참고할 도구 식별자 목록")
    category: str | None = Field(None, description="도구 카테고리")
    tags: List[str] | None = Field(None, description="도구 태그")
    description: str | None = Field(None, description="도구 설명")

    secret_id: str | None = Field(
        default=None,
        description="SecretKey secret_id (sk-*). 해당 문서의 keys[] 를 codegen 에 사용",
    )
    user_id: str = Field(default="admin", description="SecretKey 조회 user_id")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "상관관계 분석을 수행하는 도구를 만들어줘",
                "category": "finance",
                "tags": ["correlation", "analysis"],
                "description": "상관관계 분석을 수행하는 도구",
                "tools": [],
                "ref_code": "print('Hello, ToolWorld!')",
                "secret_id": "sk-a1b2c3d4e5f6",
                "user_id": "admin",
            }
        }
    )


class ToolUpdateRequest(ToolGenerateRequest):
    """도구 수정 요청"""
    query: Optional[str] = Field(
        default="도구 수정", description="도구의 기능을 재정의하거나 수정을 지시하는 자연어 질의"
    )

    # 수정 전용 필드 추가
    tool_id: str = Field(description="수정하려는 대상 도구의 고유 식별자 (ID)")
    comment: Optional[str] = Field(None, description="이번 수정 사항에 대한 간단한 코멘트")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "tool_id": "tm-1234-abcd",
                "query": "상관관계 분석 결과에 시각화 차트를 추가하도록 코드를 수정해줘",
                "category": "finance",
                "tags": ["correlation", "analysis"],
                "description": "상관관계 분석을 수행하는 도구",
                "ref_code": "print('Hello, ToolWorld!')",
                "secret_id": "sk-a1b2c3d4e5f6",
                "tools": ["tm-ref-5678ffdf"],
                "comment": "차트 출력 로직 추가",
            }
        },
    )


class ToolExecResponse(BaseModel):
    query: str = Field(description="사용자의 자연어 질의")
    result: Any = Field(description="도구 실행 결과")
    status: str = "success"

    model_config = ConfigDict(from_attributes=True)


class ToolListRequest(BaseModel):
    """도구 목록 조회 필터."""

    status: Optional[List[str]] = Field(
        default=None,
        description="도구 상태 필터 목록 (다중 선택 가능: syntax-passed, validated, failed, assetized, generated). None=전체",
    )
    secret_id: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": ["assetized", "generated"]
            }
        }
    )


class AssetizeRequest(BaseModel):
    """도구 자산화 — generate(tm-*) 또는 기존 경로(kis/stock) 모두 지원."""

    tool_id: str | None = Field(
        default=None,
        description="tool/generate 로 생성된 도구 ID (tm-*). 지정 시 해당 디렉터리를 자산화",
    )
    asset_path: str | None = Field(
        default=None,
        description="MCP HTTP 경로 (예: kis/stock). 미지정 시 tool_id 또는 tool_path 사용",
    )
    title: str | None = Field(default=None, description="도구 제목 (미지정 시 DB/경로에서 추론)")
    description: str | None = Field(default=None, description="도구 설명")
    tool_path: str | None = Field(
        default=None,
        description="원본 도구 디렉터리 (레거시). tool_id 없을 때 사용 (예: kis/stock)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tool_id": "tm-ind-ttest-e8a7c2b5",
                "asset_path": "kis/stock",
                "title": "KIS Stock",
                "description": "KIS 증권 데이터 API 도구"
            }
        }
    )

    @model_validator(mode="after")
    def check_tool_id_or_path(self) -> "AssetizeRequest":
        """tool_id와 tool_path 중 적어도 하나는 입력되었는지 검증합니다."""
        if not self.tool_id and not self.tool_path:
            raise ValueError("tool_id 또는 tool_path 중 최소 하나는 입력해야 합니다.")
        return self


class AssetizeResponse(BaseModel):
    asset_path: str = Field(description="자산화된 MCP 경로 (예: kis/stock)")
    tool_id: str = Field(description="등록된 도구 ID (asset_path 와 동일)")


class ToolRecommendRequest(BaseModel):
    """데이터셋 기반 도구 추천 요청."""

    did: str = Field(..., description="데이터셋 ID (did-*)")
    tool_category: str = Field(..., description="추천 대상 도구 카테고리")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "did": "did-stock-analysis-a1b2c3d4",
                "tool_category": "finance",
            }
        }
    )


class ToolRecommendResponse(BaseModel):
    recommended_tools: List[str] = Field(..., description="추천 도구 path 목록")


# --- secret API ---

class RegisterKeyRequest(BaseModel):
    user_id: str = Field(default="admin", description="키 소유 사용자")
    provider: str = Field(description="제공업체나 기관")
    keys: List[KeyItem] = Field(description="키 목록")
    description: str = Field(default="", description="키 용도 설명")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider": "한투",
                "keys": [{"key_name": "KIS_APP_KEY", "key_value": "1234567890"}],
                "description": "KIS API key (optional)"
            }
        }
    )


class ListKeysRequest(BaseModel):
    user_id: str = Field(default="admin", description="조회 대상 user_id")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
            }
        }
    )


class RegisteredKeyName(BaseModel):
    """등록된 키의 메타데이터 (값은 제외하고 이름만 제공)"""
    key_name: str


class SecretKeyInfo(BaseModel):
    """Key 등록 및 목록 조회 응답 — 민감한 key_value는 제외"""
    secret_id: str
    user_id: str
    provider: str  # 추가: 제공업체나 기관 구분용
    keys: List[RegisteredKeyName]  # 변경: 등록된 키 이름 목록
    description: str = ""
    created_at: str | None = None
    updated_at: str | None = None


# --- report API ---

class ReportListRequest(BaseModel):
    """리포트 목록 조회 필터."""

    status: Optional[List[str]] = Field(
        default=None,
        description="리포트 상태 필터 목록 (다중 선택 가능: completed, failed, published 등). None 또는 빈 배열=전체",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": ["completed", "published"]
            }
        }
    )


class ReportGenerateRequest(BaseModel):
    did: str = Field(..., description="데이터셋 식별자 (UUID)")
    query: str = Field(..., description="리포트 생성을 위한 사용자 요구사항/질의")
    description: Optional[str] = Field(default=None, description="보고서 부가 설명")
    tools: List[str] = Field(default_factory=list, description="참고할 도구 식별자 목록")
    session_id: str = Field(None, description="세션 식별자 (UUID)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "did": "did-test-dataset-6614b9e7",
                "query": "시가총액 기준 소형주와 대형주 간의 비교 분석",
                "description": "투자위원회 발표용 요약 보고서",
                "tools": [],
            }
        }
    )


class ReportExecRequest(BaseModel):
    rid: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"rid": "rp-bfcf8d14"}},
    )


class ReportPublishRequest(BaseModel):
    rid: str = Field(..., pattern=r"^rp-", description="발행할 보고서 ID")

    model_config = ConfigDict(
        json_schema_extra={"example": {"rid": "rp-bfcf8d14"}},
    )


class ReportAssetizeRequest(BaseModel):
    rid: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"rid": "rp-bfcf8d14"}},
    )


class ReportUpdateRequest(BaseModel):
    query: str = Field(description="사용자의 수정 요청 사항")
    rid: str = Field(pattern=r"^rp-", description="수정할 보고서 식별자 ID")
    task_ids: List[str] = Field(min_length=1, description="재생성할 태스크 ID 목록")
    tools: Optional[List[str]] = Field(default_factory=list, description="재생성 시 사용할 도구 식별자 목록")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "query": "검토 및 업데이트",
                "rid": "rp-15ad089e",
                "task_ids": ["task-cap-classification-a1b2c3d4"],
                "tools": [],
            }
        },
    )


# --- data API ---

class UnifyExecuteRequest(BaseModel):
    did: str = Field(..., description="데이터셋 ID")
    confirmed_schema: Dict[str, Any] = Field(..., description="사용자가 UI에서 최종 확정한 JSON 스키마")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "did": "did-is-gift-received-427568c1",
                "confirmed_schema": {
                    "employee_id": {"description": "사번", "title": "Employee Id", "type": "string"},
                    "name": {"description": "이름", "title": "Name", "type": "string"},
                },
            }
        }
    )


class PangeaUpdateRequest(BaseModel):
    """Pangea 스키마 갱신 API 요청 (구 UpdateRequest)."""

    did: str = Field(..., description="데이터셋 ID")
    confirmed_schema: Dict[str, Any] = Field(..., description="사용자가 UI에서 최종 확정한 JSON 스키마")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "did": "did-is-gift-received-427568c1",
                "confirmed_schema": {
                    "employee_id": {"description": "사번", "title": "Employee Id", "type": "string"},
                    "name": {"description": "이름", "title": "Name", "type": "string"},
                },
            }
        }
    )


class ReportDeleteRequest(BaseModel):
    mode: Literal["all", "list", "exclude"] = Field(
        "list",
        description="삭제 모드: 'all' (전체 삭제), 'exclude' (특정 제외 모두 삭제), 'list' (주어진 배열 삭제)"
    )
    ids: Optional[List[str]] = Field(
        default=None,
        description="mode가 'exclude'이거나 'list'일 때 사용할 rid 배열"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mode": "list",
                "ids": ["rp-e514f4b3", "rp-a3d4db1b"]
            }
        }
    )


class ToolDeleteRequest(BaseModel):
    mode: Literal["all", "list", "exclude"] = Field(
        "list",
        description="삭제 모드: 'all' (전체 삭제), 'exclude' (특정 제외 모두 삭제), 'list' (주어진 배열 삭제)"
    )
    ids: Optional[List[str]] = Field(
        default=None,
        description="mode가 'exclude'이거나 'list'일 때 사용할 tool_id 배열"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mode": "list",
                "ids": ["tm-calculator-e514f4b3", "tm-scraper-a3d4db1b"]
            }
        }
    )


class KeyDeleteRequest(BaseModel):
    mode: Literal["all", "list", "exclude"] = Field(
        "list",
        description="삭제 모드: 'all' (전체 삭제), 'exclude' (특정 제외 모두 삭제), 'list' (주어진 배열 삭제)"
    )
    ids: Optional[List[str]] = Field(
        default=None,
        description="mode가 'exclude'이거나 'list'일 때 사용할 secret_id 배열"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mode": "list",
                "ids": ["sk-a1b2c3d4e5f6"],
            }
        }
    )


class DataListRequest(BaseModel):
    """데이터셋 목록 조회 필터."""

    status: Optional[List[str]] = Field(
        default=None,
        description="데이터셋 상태 필터 목록. None 또는 빈 배열=전체",
    )
    category: Optional[str] = Field(
        default=None,
        description="데이터셋 카테고리 필터 (예: finance, hr)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": ["completed"],
                "category": "finance",
            }
        }
    )


class DataInfoRequest(BaseModel):
    """데이터셋 상세 조회."""

    did: str = Field(..., description="데이터셋 ID (did-*)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "did": "did-stock-analysis-a1b2c3d4",
            }
        }
    )


class DatasetDeleteRequest(BaseModel):
    mode: Literal["all", "list", "exclude"] = Field("list",
                                                    description="삭제 모드: 'all' (전체 삭제), 'exclude' (특정 제외 모두 삭제), 'list' (주어진 배열 삭제)")
    ids: Optional[List[str]] = Field(default=None, description="mode가 'exclude'이거나 'list'일 때 사용할 did 배열")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mode": "list",
                "ids": ["did-stock-data-e514f4b3", "did-stock-data-a3d4db1b"]
            }
        }
    )
