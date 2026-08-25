"""run_task 실행 코어 — in-process / daemon worker 공용."""

from __future__ import annotations

import importlib
import importlib.util
import json
import inspect
import os
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from utils.mod import load_module

from sage.data.bridge import InMemoryDataBridge
from sage.exec.file_reporter import FileReporter
from sage.exec.models import ExecJob, ExecResult, touch_exec_heartbeat, write_result_file
from sage.exec.shims.import_shims import exec_import_shims
from sage.exec.shims.runner_shim import setup_task_paths
from sage.models.node import TaskRun
from sage.report.context import TaskContext, TaskInfo


def _apply_worker_env(env: dict[str, str]) -> None:
    for key, value in env.items():
        os.environ[key] = value
    import importlib

    import sage.config as _cfg

    importlib.reload(_cfg)


def _ensure_host_pythonpath() -> None:
    """bind mount ``/host/n2`` 가 stale image ``sage/`` 보다 우선하도록 보장."""
    home = os.environ.get("NARRATIX_HOME", "/host/n2")
    host_root = str(Path(home).resolve())
    if host_root in sys.path:
        sys.path.remove(host_root)
    sys.path.insert(0, host_root)
    marker = Path(host_root) / "sage" / "exec" / "task_runtime.py"
    if not marker.is_file():
        raise RuntimeError(
            f"exec worker host mount incomplete — {marker} missing. "
            "Check docker-compose.exec.yml volumes (NARRATIX_HOME:/host/n2) and PYTHONPATH=/host/n2."
        )


def _resolve_entry_path(job: ExecJob) -> Path:
    entry = Path(job.entry_file)
    if entry.is_absolute():
        return entry
    return Path(job.workspace) / entry


def _ctx_from_job_args(job: ExecJob, run: TaskRun) -> TaskContext:
    """Exec worker — Mongo/원격 load 금지. snapshot 또는 ctx_path 파일만."""
    plan_id = job.args.get("plan_id") or run.plan_id
    rid = job.args.get("rid")
    snap = job.args.get("ctx_snapshot")
    if snap and snap.get("plan_id") == plan_id:
        tasks = {
            tid: TaskInfo.model_validate(task_data)
            for tid, task_data in (snap.get("tasks") or {}).items()
        }
        return TaskContext(plan_id=plan_id, tasks=tasks, rid=rid or snap.get("rid"))

    ctx_path = job.args.get("ctx_path")
    if ctx_path and Path(ctx_path).is_file():
        with open(ctx_path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("plan_id") == plan_id:
            tasks = {
                tid: TaskInfo.model_validate(task_data)
                for tid, task_data in (data.get("tasks") or {}).items()
            }
            return TaskContext(plan_id=plan_id, tasks=tasks, rid=rid or data.get("rid"))

    raise ValueError(
        f"ExecJob.args.ctx_snapshot 또는 ctx_path 필요 (plan_id={plan_id!r})"
    )


async def execute_report_task_job(job: ExecJob) -> ExecResult:
    """``report_task`` — ``run_task(run, ctx, reporter)`` 실행."""
    started = time.perf_counter()
    _apply_worker_env(job.env)

    progress_path = job.progress_file
    result_path = job.result_file
    reporter = FileReporter(progress_path)
    touch_exec_heartbeat(job)

    try:
        _ensure_host_pythonpath()

        source_path = _resolve_entry_path(job)
        if not source_path.is_file():
            raise FileNotFoundError(f"태스크 소스 없음: {source_path}")

        run_payload = job.args.get("run")
        if not run_payload:
            raise ValueError("ExecJob.args.run 필요")
        run = TaskRun.model_validate(run_payload)

        ctx = _ctx_from_job_args(job, run)

        import sage.data.schema_types as _schema_types_mod
        import sage.data.schema_contract as _schema_contract_mod
        import sage.data.pangea as _pangea_mod
        importlib.reload(_schema_types_mod)
        importlib.reload(_schema_contract_mod)
        importlib.reload(_pangea_mod)

        setup_task_paths()
        mod_name = f"p2_exec_{run.task_id.replace('-', '_')}"
        exec_source = source_path.read_text(encoding="utf-8")
        filename = str(source_path.resolve())

        code_obj = compile(exec_source, filename, "exec")
        module = importlib.util.module_from_spec(
            importlib.util.spec_from_loader(mod_name, loader=None)
        )
        assert module is not None
        module.__dict__["__builtins__"] = __builtins__
        module.__dict__["__name__"] = mod_name
        module.__dict__["__file__"] = filename
        with exec_import_shims():
            exec(code_obj, module.__dict__)

        run_fn = module.run_task
        kwargs: dict[str, Any] = {}
        if "reporter" in inspect.signature(run_fn).parameters:
            kwargs["reporter"] = reporter

        result = run_fn(run, ctx, **kwargs)
        if hasattr(result, "__await__"):
            await result

        ctx.save()
        reporter.update(f"✓ [{run.title}] 완료", state="completed")

        duration_ms = int((time.perf_counter() - started) * 1000)
        exec_result = ExecResult(
            ok=True,
            job_id=job.job_id,
            return_value={"plan_id": ctx.plan_id, "task_id": run.task_id},
            duration_ms=duration_ms,
            exit_code=0,
        )
        write_result_file(result_path, exec_result)
        return exec_result

    except Exception as exc:
        err = traceback.format_exc()
        reporter.update(f"실행 실패: {exc}", state="failed")
        duration_ms = int((time.perf_counter() - started) * 1000)
        exec_result = ExecResult(
            ok=False,
            job_id=job.job_id,
            error=err,
            stderr_tail=err[-8000:],
            duration_ms=duration_ms,
            exit_code=1,
        )
        write_result_file(result_path, exec_result)
        return exec_result
    finally:
        prefix = "p2_exec_"
        for name in list(sys.modules):
            if name.startswith(prefix):
                sys.modules.pop(name, None)


def _invalidate_pangea_modules() -> None:
    for name in ("schema", "adapter", "unify"):
        sys.modules.pop(name, None)


def _dataset_root_from_pangea_path(pangea_path: Path) -> Path:
    # ``data/{did}/pangea/vN`` → ``data/{did}``
    return pangea_path.parent.parent


async def execute_pangea_unify_job(job: ExecJob) -> ExecResult:
    """``pangea_unify`` — ``unify_data(did, reporter)`` + parquet 산출."""
    started = time.perf_counter()
    _apply_worker_env(job.env)

    progress_path = job.progress_file
    result_path = job.result_file
    reporter = FileReporter(progress_path)
    touch_exec_heartbeat(job)

    try:
        _ensure_host_pythonpath()
        did = job.args.get("did")
        if not did:
            raise ValueError("ExecJob.args.did 필요")

        workspace = Path(job.workspace)
        dataset_root = _dataset_root_from_pangea_path(workspace)
        InMemoryDataBridge.import_staging(did, dataset_root / ".bridge")

        _invalidate_pangea_modules()
        for name in ("schema", "adapter"):
            load_module(name, workspace / f"{name}.py")

        unify_path = workspace / "unify.py"
        if not unify_path.is_file():
            raise FileNotFoundError(f"unify.py 없음: {unify_path}")

        with exec_import_shims():
            unify_mod = load_module("unify", unify_path)
        unify_func = getattr(unify_mod, "unify_data")

        kwargs: dict[str, Any] = {}
        if "reporter" in inspect.signature(unify_func).parameters:
            kwargs["reporter"] = reporter

        results = unify_func(did, **kwargs)
        if hasattr(results, "__await__"):
            results = await results

        if reporter.status == "failed":
            raise RuntimeError("unify_data 가 failed 상태로 종료되었습니다.")
        if not isinstance(results, dict):
            raise TypeError(
                f"unify_data 는 Dict[str, DataFrame] 을 반환해야 합니다 "
                f"(got {type(results).__name__})"
            )

        empty = []
        for key, df in results.items():
            try:
                n = 0 if df is None else int(len(df))
            except Exception:
                n = 0
            if n == 0:
                empty.append(str(key))
        if empty:
            raise RuntimeError(
                "unify_data 가 0행 DataFrame 을 반환했습니다: "
                + ", ".join(empty)
                + ". 도구 FAIL·빈 응답을 성공 parquet 으로 저장하지 마세요. "
                "status!=SUCCESS 이면 raise 하세요. 파일 소스가 없으면 질의 선정 목록으로 도구를 호출하세요."
            )

        keys: list[str] = []
        for key, df in results.items():
            out_path = workspace / f"{key}.parquet"
            df.to_parquet(out_path, index=False)
            keys.append(key)

        duration_ms = int((time.perf_counter() - started) * 1000)
        exec_result = ExecResult(
            ok=True,
            job_id=job.job_id,
            return_value={"keys": keys},
            duration_ms=duration_ms,
            exit_code=0,
        )
        write_result_file(result_path, exec_result)
        return exec_result

    except Exception as exc:
        err = traceback.format_exc()
        reporter.update(f"실행 실패: {exc}", state="failed")
        duration_ms = int((time.perf_counter() - started) * 1000)
        exec_result = ExecResult(
            ok=False,
            job_id=job.job_id,
            error=err,
            stderr_tail=err[-8000:],
            duration_ms=duration_ms,
            exit_code=1,
        )
        write_result_file(result_path, exec_result)
        return exec_result
    finally:
        _invalidate_pangea_modules()


async def execute_tool_caller_job(job: ExecJob) -> ExecResult:
    """``tool_caller`` — ``caller.py:main(**kwargs)`` + JSON 직렬화 검증."""
    started = time.perf_counter()
    _apply_worker_env(job.env)

    progress_path = job.progress_file
    result_path = job.result_file
    reporter = FileReporter(progress_path)
    touch_exec_heartbeat(job)
    module_name = f"caller_exec_{uuid.uuid4().hex[:8]}"

    try:
        _ensure_host_pythonpath()
        workspace = Path(job.workspace)
        caller_path = workspace / "caller.py"
        if not caller_path.is_file():
            raise FileNotFoundError(f"caller.py 없음: {caller_path}")

        spec = importlib.util.spec_from_file_location(module_name, str(caller_path))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"caller 모듈 spec 생성 실패: {caller_path}")

        module = importlib.util.module_from_spec(spec)
        module.__dict__["pd"] = pd
        module.__dict__["np"] = np
        sys.modules[module_name] = module
        with exec_import_shims():
            spec.loader.exec_module(module)

        if not hasattr(module, "main"):
            raise RuntimeError("main() 함수를 찾을 수 없습니다.")

        main_fn = module.main
        call_kwargs = dict(job.args.get("kwargs") or {})
        sig = inspect.signature(main_fn)
        if call_kwargs:
            call_kwargs = {
                key: value for key, value in call_kwargs.items() if key in sig.parameters
            }

        fn_kwargs: dict[str, Any] = {}
        if "reporter" in sig.parameters:
            fn_kwargs["reporter"] = reporter
        fn_kwargs.update(call_kwargs)

        if call_kwargs or fn_kwargs:
            result = main_fn(**fn_kwargs)
        else:
            result = main_fn()

        if hasattr(result, "__await__"):
            result = await result

        try:
            cleaned = json.loads(json.dumps(result, ensure_ascii=False))
        except Exception as exc:
            raise RuntimeError(f"데이터 직렬화 실패: {exc}") from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        exec_result = ExecResult(
            ok=True,
            job_id=job.job_id,
            return_value={"result": cleaned},
            duration_ms=duration_ms,
            exit_code=0,
        )
        write_result_file(result_path, exec_result)
        return exec_result

    except Exception as exc:
        err = traceback.format_exc()
        reporter.update(f"실행 실패: {exc}", state="failed")
        duration_ms = int((time.perf_counter() - started) * 1000)
        exec_result = ExecResult(
            ok=False,
            job_id=job.job_id,
            error=err,
            stderr_tail=err[-8000:],
            duration_ms=duration_ms,
            exit_code=1,
        )
        write_result_file(result_path, exec_result)
        return exec_result
    finally:
        sys.modules.pop(module_name, None)


async def execute_job(job: ExecJob) -> ExecResult:
    if job.kind == "report_task":
        return await execute_report_task_job(job)
    if job.kind == "pangea_unify":
        return await execute_pangea_unify_job(job)
    if job.kind == "tool_caller":
        return await execute_tool_caller_job(job)
    return ExecResult(
        ok=False,
        job_id=job.job_id,
        error=f"unsupported kind: {job.kind}",
        exit_code=1,
    )
