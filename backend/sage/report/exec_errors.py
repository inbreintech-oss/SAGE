"""Exec 인프라 vs 생성 task 소스 오류 구분 — codegen 재시도 정책."""

from __future__ import annotations

# traceback / result.error 에 아래가 있으면 LLM 재생성 무의미
_PLATFORM_MARKERS: tuple[str, ...] = (
    "sage/exec/worker_core.py",
    "sage\\exec\\worker_core.py",
    "/host/n2/sage/exec/worker_core.py",
    "sage/exec/daemon.py",
    "sage/exec/runtime.py",
    "sage/exec/drivers/docker_pool",
    "exec stall",
    "exec timeout",
    "exec pool",
    "docker_pool",
    "docker exec pool",
    "daemon job timeout",
    "host mount incomplete",
    "exec worker host mount",
    "ExecJob.result_file required",
    "function' object has no attribute 'submit'",
)

# 생성 task 모듈 — 이 경로면 worker 가 아니라 LLM codegen 쪽
_TASK_SOURCE_MARKERS: tuple[str, ...] = (
    "p2_exec_",
    "/srcs/task-",
    "\\srcs\\task-",
    "reports/rp-",
    "reports\\rp-",
)


def is_exec_platform_error(text: str) -> bool:
    """True → exec worker / pool 버그·인프라. codegen 재호출 금지."""
    if not (text or "").strip():
        return False
    blob = text
    # task srcs/*.py 가 traceback 에 있으면 LLM 소스 오류 — 재생성 대상
    if any(m in blob for m in _TASK_SOURCE_MARKERS):
        return False

    lower = blob.lower()
    for marker in _PLATFORM_MARKERS:
        if marker.lower() in lower:
            return True

    return False


class ExecPlatformError(Exception):
    """Exec worker / docker pool 실패 — LLM codegen 으로는 해결 불가."""
