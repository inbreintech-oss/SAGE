"""Container-internal HTTP daemon — warm pool worker (:9000)."""

from __future__ import annotations

import asyncio
import concurrent.futures
import time
import traceback
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from sage.exec.models import ExecJob, ExecResult, touch_exec_heartbeat, write_result_file

_jobs: dict[str, dict[str, Any]] = {}
_state_lock = asyncio.Lock()
_executor_pool: concurrent.futures.ThreadPoolExecutor | None = None


def _get_executor_pool() -> concurrent.futures.ThreadPoolExecutor:
    """HTTP 이벤트 루프와 분리 — sync run_task 가 /health 를 막지 않게."""
    global _executor_pool
    if _executor_pool is None:
        _executor_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="sage-exec-job",
        )
    return _executor_pool


def _execute_job_blocking(job: ExecJob) -> ExecResult:
    # bind mount 로 host 코드가 바뀌어도 daemon 프로세스는 import 캐시를 유지 — job 마다 reload
    import importlib

    import sage.exec.worker_core as worker_core

    importlib.reload(worker_core)
    return asyncio.run(worker_core.execute_job(job))


def _ensure_result_on_disk(job: ExecJob, result: ExecResult) -> None:
    """Worker crash 시에도 host 가 result 파일로 완료를 감지."""
    if not job.result_file:
        return
    path = Path(job.result_file)
    if path.is_file():
        return
    write_result_file(job.result_file, result)


async def _health(_: Request) -> JSONResponse:
    async with _state_lock:
        running = sum(1 for j in _jobs.values() if j.get("status") == "running")
    return JSONResponse(
        {
            "status": "busy" if running else "idle",
            "running_jobs": running,
            "total_jobs": len(_jobs),
        }
    )


async def _get_exec(request: Request) -> JSONResponse:
    """Stall fail-fast 시 host one-shot fallback (poll loop 아님)."""
    job_id = request.path_params["job_id"]
    async with _state_lock:
        entry = _jobs.get(job_id)
    if not entry:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(entry)


async def _post_exec(request: Request) -> JSONResponse:
    payload = await request.json()
    job = ExecJob.from_dict(payload)
    async with _state_lock:
        if job.job_id in _jobs and _jobs[job.job_id].get("status") == "running":
            return JSONResponse({"error": "job already running"}, status_code=409)
        _jobs[job.job_id] = {"status": "running", "started_at": time.time()}

    touch_exec_heartbeat(job)

    async def _run() -> None:
        result: ExecResult | None = None
        try:
            loop = asyncio.get_running_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(_get_executor_pool(), _execute_job_blocking, job),
                timeout=float(job.limits.timeout_sec + 30),
            )
            async with _state_lock:
                _jobs[job.job_id] = {
                    "status": "completed" if result.ok else "failed",
                    "result": result.to_dict(),
                }
        except asyncio.TimeoutError:
            err = f"daemon job timeout ({job.limits.timeout_sec}s)"
            result = ExecResult(
                ok=False,
                job_id=job.job_id,
                error=err,
                stderr_tail=err,
                exit_code=124,
            )
            async with _state_lock:
                _jobs[job.job_id] = {"status": "failed", "result": result.to_dict()}
        except Exception as exc:
            err = traceback.format_exc()
            result = ExecResult(
                ok=False,
                job_id=job.job_id,
                error=err,
                stderr_tail=err[-8000:],
                exit_code=1,
            )
            async with _state_lock:
                _jobs[job.job_id] = {"status": "failed", "result": result.to_dict()}
        finally:
            if result is not None:
                _ensure_result_on_disk(job, result)

    asyncio.create_task(_run())
    return JSONResponse({"accepted": True, "job_id": job.job_id})


async def _post_reset(_: Request) -> JSONResponse:
    import sys

    async with _state_lock:
        stale = [
            jid
            for jid, entry in _jobs.items()
            if entry.get("status") != "running"
        ]
        for jid in stale:
            _jobs.pop(jid, None)
    for name in list(sys.modules):
        if name.startswith("p2_exec_") or name in {"unify", "schema", "adapter"}:
            sys.modules.pop(name, None)
    return JSONResponse({"status": "idle"})


def create_daemon_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/health", _health, methods=["GET"]),
            Route("/exec/{job_id}", _get_exec, methods=["GET"]),
            Route("/exec", _post_exec, methods=["POST"]),
            Route("/reset", _post_reset, methods=["POST"]),
        ],
    )


def main() -> None:
    import os

    import uvicorn

    port = int(os.environ.get("SAGE_EXEC_DAEMON_PORT", "9000"))
    host = os.environ.get("SAGE_EXEC_DAEMON_HOST", "0.0.0.0")
    uvicorn.run(create_daemon_app(), host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
