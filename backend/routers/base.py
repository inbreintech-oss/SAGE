"""공통 API 응답 래퍼 및 SSE 인코더.

모든 REST 라우터는 APIResponse[T] 로 success/error/result 를 통일하고,
스트리밍 API(data/report/tool generate)는 SSEEncoder 로 event+data JSON 을 내보냅니다.
"""

import json
from typing import TypeVar, Generic, Optional

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from sage.logg import error

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool
    error: Optional[str] = Field(None, description="오류 메시지")
    result: Optional[T] = Field(None, description="결과")

    @model_validator(mode='after')
    def log_error_if_exists(self) -> 'APIResponse':
        # success가 False이거나 error 메시지가 있는 경우 로그 기록
        if not self.success or self.error:
            log_msg = self.error or "Unknown error occurred in APIResponse"
            # sage.logg에서 임포트한 error 함수 사용
            error(f"[API_ERROR] {log_msg}")
        return self

# class SseBaseModel(BaseModel):
#     """
#     모든 SSE 응답 모델의 기반이 되는 베이스 모델입니다.
#     """
#     model_config = ConfigDict(
#         populate_by_name=True,
#         arbitrary_types_allowed=True
#     )
#
#     def to_sse(self) -> bytes:
#         """
#         Pydantic 모델을 SSE(Server-Sent Events) 규격의 문자열로 변환합니다.
#         [2026-02-04] ensure_ascii=False 옵션을 적용하여 한글 깨짐을 방지합니다.
#         """
#         # exclude_none=True를 통해 필드 값이 None인 항목은 JSON에서 제외합니다.
#         json_str = json.dumps(
#             self.model_dump(exclude_none=True, by_alias=True),
#             ensure_ascii=False
#         )
#         return f"data: {json_str}\n\n".encode("utf-8")

# class ReportStatus(SseBaseModel):
#     """
#     리포트 생성 단계별 상태를 전송하기 위한 모델입니다.
#     """
#     status: str = Field(..., description="현재 프로세스 상태 (planning, executing, complete, error 등)")
#     msg: Optional[str] = Field(None, description="사용자에게 노출할 상태 메시지")
#     rid: Optional[str] = Field(None, description="Report ID (식별자)")
#     pid: Optional[str] = Field(None, description="Plan ID (식별자)")
#     task_id: Optional[str] = Field(None, description="현재 실행 중인 작업 ID")
#     content: Optional[str] = Field(None, description="생성된 마크다운 또는 텍스트 콘텐츠")
#     error_detail: Optional[Any] = Field(None, description="에러 발생 시 상세 정보")
#
#     # 예시 데이터 생성 (검증용)
#     model_config = ConfigDict(
#         json_schema_extra={
#             "example": {
#                 "status": "executing",
#                 "msg": "데이터 분석 중...",
#                 "rid": "rp-20260210-abcd",
#                 "task_id": "task-001"
#             }
#         }
#     )

# class SourceMetadata(BaseModel):
#     source_id: str
#     columns: List[str]
#     column_types: Optional[Dict[str, str]] = None
#     column_descriptions: Optional[Dict[str, str]] = None
#     sample_data: Optional[List[Dict[str, Any]]] = None
#     description: Optional[str] = None
#
#
# class DataAnalysisInput(BaseModel):
#     dataset_name: str
#     user_query: Optional[str] = ""
#     sources: List[SourceMetadata]

# --- 통합 타입 정의 ---

# class DeleteRequest(BaseModel):
#     id: str = Field(..., description="삭제할 도구의 고유 ID")
#     reason: Optional[str] = Field(None, description="삭제 사유 (선택 사항)")
#
#     # Pydantic v2.0 설정
#     model_config = ConfigDict(from_attributes=True)

class DeleteResponse(BaseModel):
    status: str
    id: str
    message: str

    model_config = ConfigDict(from_attributes=True)

# class SSEEncoder:
#     """SSE 메시지 객체 생성을 전담 (EventSourceResponse 호환)"""
#
#     @staticmethod
#     # def encode(status: str, msg: str, **kwargs) -> dict:
#     #     # dict로 반환하면 sse-starlette이 자동으로 SSE 규격으로 감싸줌
#     #     return {
#     #         "event": status,  # 클라이언트에서 event 리스너로 분기 가능
#     #         "data": json.dumps({
#     #             # "status": status,
#     #             "msg": msg,
#     #             **kwargs
#     #         }, ensure_ascii=False)
#     #     }

class SSEEncoder:
    """EventSourceResponse 호환 dict 생성 — Pydantic/nested 객체를 JSON-safe 로 직렬화."""

    @staticmethod
    def encode(status: str, msg: str, **kwargs):
        processed_kwargs = {}
        for k, v in kwargs.items():
            # Pydantic v2.0 모델 처리
            if isinstance(v, BaseModel):
                processed_kwargs[k] = v.model_dump(mode='json')
            else:
                # list[dict], 중첩 구조 등 임의 타입 → JSON 호환 Python 타입
                processed_kwargs[k] = TypeAdapter(type(v)).dump_python(v, mode='json')

        return {
            "event": status,
            "data": json.dumps({
                "event": status,
                "msg": msg,
                **processed_kwargs
            }, ensure_ascii=False)
        }
