"""Exec runtime — docker_pool only (fail-fast, no in-process fallback)."""

from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path

import cfg
from sage.exec.models import ExecJob, ExecResult
from sage.logg import error, info


def _require_docker_pool() -> None:
    driver = (cfg.sage_exec_driver or "").strip().lower()
    if driver != "docker_pool":
        raise RuntimeError(
            f"SAGE_EXEC_DRIVER must be docker_pool (got {driver!r}). "
            "In-process exec is not supported."
        )


def _docker_pool_failure_result(job: ExecJob, exc: Exception) -> ExecResult:
    msg = (
        "Docker exec pool 실패 — 격리 실행을 완료하지 못했습니다. "
        "`docker compose -f docker-compose.exec.yml ps` 로 worker 상태를 확인하세요. "
        f"원인: {exc}"
    )
    error(msg)
    return ExecResult(
        ok=False,
        job_id=job.job_id,
        error=msg,
        stderr_tail=str(exc)[-8000:],
        exit_code=125,
    )


async def run_exec_job(job: ExecJob, *, reporter=None) -> ExecResult:
    """모든 격리 exec 의 단일 진입점 — report / pangea / tool.

    ``reporter`` 가 있으면 ``job.progress_file`` 을 tail 하며 ``reporter.update`` 호출.
    """
    _require_docker_pool()
    info(f"[exec:docker_pool] start kind={job.kind} job_id={job.job_id}")

    async def _dispatch() -> ExecResult:
        try:
            from sage.exec.drivers.docker_pool import run_docker_pool

            result = await run_docker_pool(job)
        except Exception as exc:
            return _docker_pool_failure_result(job, exc)

        info(
            f"[exec:docker_pool] end kind={job.kind} job_id={job.job_id} "
            f"ok={result.ok} duration_ms={result.duration_ms}"
        )
        return result

    if reporter is None:
        return await _dispatch()

    stop = asyncio.Event()
    pos = 0

    async def _tail() -> None:
        nonlocal pos
        while not stop.is_set():
            if job.progress_file:
                pos = await tail_progress_file(
                    job.progress_file,
                    last_pos=pos,
                    on_line=lambda msg, state: reporter.update(msg, state=state),
                )
            await asyncio.sleep(0.05)

    tail_task = asyncio.create_task(_tail())
    try:
        return await _dispatch()
    finally:
        stop.set()
        tail_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tail_task
        if job.progress_file:
            await tail_progress_file(
                job.progress_file,
                last_pos=pos,
                on_line=lambda msg, state: reporter.update(msg, state=state),
            )


async def tail_progress_file(
    path: str | Path,
    *,
    last_pos: int = 0,
    on_line,
) -> int:
    """NDJSON progress tail — ``on_line(msg, state)``."""
    p = Path(path)
    if not p.is_file():
        return last_pos
    text = p.read_text(encoding="utf-8")
    if len(text) <= last_pos:
        return last_pos
    chunk = text[last_pos:]
    for line in chunk.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            on_line(data.get("msg", ""), data.get("state", "running"))
        except json.JSONDecodeError:
            on_line(line, "running")
    return len(text)


async def run_tool_caller(
    workspace: Path,
    *,
    kwargs: dict | None = None,
    reporter=None,
) -> ExecResult:
    """``tool_caller`` — ``caller.py:main`` (report/pangea 와 동일 exec 경로)."""
    from sage.exec.jobs import build_tool_caller_job

    caller_py = workspace / "caller.py"
    if not caller_py.is_file():
        raise FileNotFoundError("caller.py 파일이 존재하지 않습니다.")

    job = build_tool_caller_job(workspace=workspace, kwargs=kwargs or {})
    return await run_exec_job(job, reporter=reporter)
