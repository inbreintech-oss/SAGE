import traceback
from typing import Optional


def format_exception(
    exc: BaseException | None,
    *,
    context: Optional[str] = None,
    include_traceback: bool = True,
) -> str:
    """예외 타입, 메시지, 원인 체인, traceback을 포함한 상세 문자열을 반환합니다."""
    if exc is None:
        return context or "알 수 없는 오류"

    lines: list[str] = []
    if context:
        lines.append(context)

    lines.append(f"{type(exc).__name__}: {exc}")

    for attr in ("response", "body", "status_code", "code", "details", "data"):
        if hasattr(exc, attr):
            value = getattr(exc, attr)
            if value is not None:
                lines.append(f"  {attr}: {value}")

    seen = {id(exc)}
    current = exc
    while True:
        nxt = current.__cause__
        label = "원인"
        if nxt is None and current.__context__ and not current.__suppress_context__:
            nxt = current.__context__
            label = "컨텍스트"
        if nxt is None or id(nxt) in seen:
            break
        seen.add(id(nxt))
        lines.append(f"  └─ {label}: {type(nxt).__name__}: {nxt}")
        current = nxt

    if include_traceback and exc.__traceback__ is not None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip()
        if tb:
            lines.append("Traceback:")
            lines.append(tb)

    return "\n".join(lines)


class DataNotFoundError(Exception):
    """데이터 정보를 찾을 수 없을 때 발생하는 커스텀 예외"""

    def __init__(self, did: str):
        self.did = did
        self.message = f"Data {did} 정보를 찾을 수 없습니다."
        super().__init__(self.message)

class ExecutionError(Exception):
    pass

class ServiceUnavailableError(Exception):
    def __init__(self, message="LLM 서버 사용 불가, 잠시 후 서비스 이용 바랍니다"):
        self.message = message
        super().__init__(self.message)

class QuotaExceededError(ServiceUnavailableError):
    """LLM API quota / spend cap — 재시도 무의미."""

    def __init__(
        self,
        message="LLM API 사용 한도 초과(429) — AI Studio spend cap 확인 또는 SAGE_LLM_TYPE 변경",
    ):
        super().__init__(message)

class LLMTimeoutError(ServiceUnavailableError):
    """LLM 요청 응답 없음 — timeout."""

    def __init__(self, timeout_sec: float = 120):
        self.timeout_sec = timeout_sec
        super().__init__(f"LLM 응답 없음 — {timeout_sec:.0f}초 timeout")

def is_quota_error(exc: BaseException | str | None) -> bool:
    if exc is None:
        return False
    s = str(exc)
    return (
        "429" in s
        or "RESOURCE_EXHAUSTED" in s
        or "exceeded its monthly spending" in s
        or "QuotaExceeded" in s
    )

class ContextStorageError(ValueError):
    """TaskContext 저장 형식 위반 — json(dict/list) 집계·선별 데이터만 허용."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ContextPayloadTooLargeError(ContextStorageError):
    """단일 context key JSON payload 크기 초과."""

    def __init__(self, size_bytes: int, limit_bytes: int, *, key_hint: str = ""):
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes
        hint = f" ({key_hint})" if key_hint else ""
        self.message = (
            f"TaskContext JSON payload{hint} 크기 초과: {size_bytes:,}B > limit {limit_bytes:,}B — "
            "통계·선별·집계 결과만 최소한으로 저장하세요."
        )
        super().__init__(self.message)


class ContextAttachTooLargeError(ContextStorageError):
    """llm_attach 전체 패킷 크기 초과 — generate 호출 거부."""

    def __init__(self, size_bytes: int, limit_bytes: int):
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes
        self.message = (
            f"llm_attach 패킷 크기 초과: {size_bytes:,}B > limit {limit_bytes:,}B — "
            "upstream context 를 축소하거나 집계 결과만 남기세요."
        )
        super().__init__(self.message)


class MaxRetriesExceededError(Exception):
    def __init__(self, max_retries=3, last_error: str | None = None):
        self.max_retries = max_retries
        self.last_error = last_error or ""
        self.message = f"최대 재시도({max_retries}) 초과 오류"
        if self.last_error:
            lines = [ln.strip() for ln in self.last_error.strip().splitlines() if ln.strip()]
            useful = [
                ln
                for ln in lines
                if not ln.startswith("준수 계약")
                and "동일 contract 위반" not in ln
            ]
            snippet = " ".join(useful) if useful else self.last_error.strip()
            self.message = f"{self.message}: {snippet[:800]}"
        super().__init__(self.message)


class CodegenContractError(Exception):
    """instruction contract 위반 — NodeV 가 llm_retry=False 일 때 발생.

    runner 는 같은 generate 안에서 소스 재생성한다 (사용자 재요청 아님).
    """

    def __init__(self, message: str, *, category: str = ""):
        self.message = message
        self.category = category
        super().__init__(message)
