"""ExecJob 빌더 — report runner 연동."""

from __future__ import annotations

import uuid
from pathlib import Path

import cfg

from sage.exec.models import ExecJob, ExecLimits, ExecMount, ensure_parent
from sage.models.node import TaskRun
from sage.report.context import TaskContext


def _host_mount_root() -> str:
    return str(Path(cfg.root_path).resolve())


def _container_path_for_host(host_path: Path) -> str:
    """Warm pool — ``NARRATIX_HOME:/host/n2`` 단일 mount 기준."""
    root = Path(cfg.root_path).resolve()
    rel = host_path.resolve().relative_to(root)
    return str(Path("/host/n2") / rel).replace("\\", "/")


def build_report_task_job(
    *,
    source_path: Path,
    run: TaskRun,
    ctx: TaskContext,
    rid: str,
    network: str = "mcp_only",
) -> ExecJob:
    job_id = f"ej-{uuid.uuid4().hex[:12]}"
    report_dir = source_path.parent.parent
    exec_dir = report_dir / ".exec"
    progress_file = exec_dir / f"{job_id}.progress.ndjson"
    result_file = exec_dir / f"{job_id}.result.json"
    ensure_parent(progress_file)
    ensure_parent(result_file)

    dump_dir = Path(cfg.dump_path) / ctx.plan_hex
    data_dir = Path(cfg.root_path) / "data" / run.data_id

    mounts: list[ExecMount] = [
        ExecMount(_host_mount_root(), "/host/n2", "rw"),
    ]

    mcp_base = cfg.sage_mcp_base_url or f"http://host.docker.internal:{cfg.port + 1}"

    return ExecJob(
        kind="report_task",
        job_id=job_id,
        workspace=str(report_dir.resolve()),
        entry_file=str(source_path.resolve().relative_to(report_dir.resolve())),
        entry_callable="run_task",
        args={
            "run": run.model_dump(),
            "plan_id": run.plan_id,
            "rid": rid,
            "ctx_snapshot": ctx.to_dict(),
            "ctx_path": str(dump_dir / "context.json"),
            "data_id": run.data_id,
        },
        env={
            "NARRATIX_HOME": "/host/n2",
            "PYTHONPATH": "/host/n2",
            "SAGE_MCP_BASE_URL": mcp_base,
            "PYTHONUTF8": "1",
        },
        limits=ExecLimits(timeout_sec=cfg.sage_exec_timeout_sec),
        network=network,  # type: ignore[arg-type]
        mounts=mounts,
        progress_file=str(progress_file.resolve()),
        result_file=str(result_file.resolve()),
    )


def build_pangea_unify_job(
    *,
    did: str,
    pangea_path: Path,
    network: str = "mcp_only",
) -> ExecJob:
    """``pangea_unify`` — ``unify.py:unify_data(did, reporter)``."""
    job_id = f"ej-{uuid.uuid4().hex[:12]}"
    exec_dir = pangea_path / ".exec"
    progress_file = exec_dir / f"{job_id}.progress.ndjson"
    result_file = exec_dir / f"{job_id}.result.json"
    ensure_parent(progress_file)
    ensure_parent(result_file)

    mounts: list[ExecMount] = [
        ExecMount(_host_mount_root(), "/host/n2", "rw"),
    ]

    mcp_base = cfg.sage_mcp_base_url or f"http://host.docker.internal:{cfg.port + 1}"

    return ExecJob(
        kind="pangea_unify",
        job_id=job_id,
        workspace=str(pangea_path.resolve()),
        entry_file="unify.py",
        entry_callable="unify_data",
        args={"did": did},
        env={
            "NARRATIX_HOME": "/host/n2",
            "PYTHONPATH": "/host/n2",
            "SAGE_MCP_BASE_URL": mcp_base,
            "PYTHONUTF8": "1",
        },
        limits=ExecLimits(timeout_sec=cfg.sage_exec_timeout_sec),
        network=network,  # type: ignore[arg-type]
        mounts=mounts,
        progress_file=str(progress_file.resolve()),
        result_file=str(result_file.resolve()),
    )


def build_tool_caller_job(
    *,
    workspace: Path,
    kwargs: dict | None = None,
    network: str = "mcp_only",
) -> ExecJob:
    """``tool_caller`` — ``caller.py:main(**kwargs)``."""
    job_id = f"ej-{uuid.uuid4().hex[:12]}"
    exec_dir = workspace / ".exec"
    progress_file = exec_dir / f"{job_id}.progress.ndjson"
    result_file = exec_dir / f"{job_id}.result.json"
    ensure_parent(progress_file)
    ensure_parent(result_file)

    mounts: list[ExecMount] = [
        ExecMount(_host_mount_root(), "/host/n2", "rw"),
    ]

    mcp_base = cfg.sage_mcp_base_url or f"http://host.docker.internal:{cfg.port + 1}"

    return ExecJob(
        kind="tool_caller",
        job_id=job_id,
        workspace=str(workspace.resolve()),
        entry_file="caller.py",
        entry_callable="main",
        args={"kwargs": kwargs or {}},
        env={
            "NARRATIX_HOME": "/host/n2",
            "PYTHONPATH": "/host/n2",
            "SAGE_MCP_BASE_URL": mcp_base,
            "PYTHONUTF8": "1",
        },
        limits=ExecLimits(timeout_sec=cfg.sage_exec_timeout_sec),
        network=network,  # type: ignore[arg-type]
        mounts=mounts,
        progress_file=str(progress_file.resolve()),
        result_file=str(result_file.resolve()),
    )


def translate_job_for_container(job: ExecJob) -> ExecJob:
    """호스트 경로 → 컨테이너 내부 경로 (daemon worker용)."""
    root = Path(cfg.root_path).resolve()
    workspace = Path(job.workspace).resolve()
    entry = Path(job.entry_file)
    if not entry.is_absolute():
        entry = workspace / entry

    container_workspace = _container_path_for_host(workspace)
    container_entry = _container_path_for_host(entry)

    def _xlate(path: str | None) -> str | None:
        if not path:
            return None
        p = Path(path).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            return path
        return _container_path_for_host(p)

    args = dict(job.args)
    if args.get("ctx_path"):
        args["ctx_path"] = _xlate(args["ctx_path"])

    return ExecJob(
        kind=job.kind,
        job_id=job.job_id,
        workspace=container_workspace,
        entry_file=container_entry,
        entry_callable=job.entry_callable,
        args=args,
        env=dict(job.env),
        limits=job.limits,
        network=job.network,
        mounts=job.mounts,
        progress_file=_xlate(job.progress_file),
        result_file=_xlate(job.result_file),
    )
