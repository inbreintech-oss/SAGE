"""ExecJob / ExecResult — control plane ↔ worker 계약."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


ExecKind = Literal["report_task", "pangea_unify", "tool_caller"]
NetworkMode = Literal["deny", "mcp_only"]
MountMode = Literal["ro", "rw"]
JobStatus = Literal["pending", "running", "completed", "failed"]


@dataclass
class ExecMount:
    host_path: str
    container_path: str
    mode: MountMode = "rw"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecLimits:
    timeout_sec: int = 600
    mem_mb: int | None = 512
    cpu: float | None = None
    pids_limit: int | None = 256

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecJob:
    kind: ExecKind
    job_id: str
    workspace: str
    entry_file: str
    entry_callable: str
    args: dict[str, Any] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    limits: ExecLimits = field(default_factory=ExecLimits)
    network: NetworkMode = "mcp_only"
    mounts: list[ExecMount] = field(default_factory=list)
    progress_file: str | None = None
    result_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["limits"] = self.limits.to_dict()
        payload["mounts"] = [m.to_dict() for m in self.mounts]
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecJob:
        limits = ExecLimits(**(data.get("limits") or {}))
        mounts = [ExecMount(**m) for m in (data.get("mounts") or [])]
        return cls(
            kind=data["kind"],
            job_id=data["job_id"],
            workspace=data["workspace"],
            entry_file=data["entry_file"],
            entry_callable=data["entry_callable"],
            args=data.get("args") or {},
            env=data.get("env") or {},
            limits=limits,
            network=data.get("network", "mcp_only"),
            mounts=mounts,
            progress_file=data.get("progress_file"),
            result_file=data.get("result_file"),
        )


@dataclass
class ExecResult:
    ok: bool
    job_id: str
    return_value: Any | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0
    exit_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecResult:
        return cls(
            ok=bool(data.get("ok")),
            job_id=data.get("job_id", ""),
            return_value=data.get("return_value"),
            stdout_tail=data.get("stdout_tail") or "",
            stderr_tail=data.get("stderr_tail") or "",
            artifacts=list(data.get("artifacts") or []),
            error=data.get("error"),
            duration_ms=int(data.get("duration_ms") or 0),
            exit_code=data.get("exit_code"),
        )


def ensure_parent(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_result_file(path: str | Path | None, result: ExecResult) -> None:
    """Worker/daemon 공용 — result.json atomic-ish write."""
    if not path:
        return
    ensure_parent(path).write_text(result.to_json(), encoding="utf-8")


def heartbeat_path(job: ExecJob) -> Path | None:
    """Stall 감지 전용 — 사용자 progress(SSE) 와 분리."""
    if not job.progress_file:
        return None
    return Path(job.progress_file).parent / f"{job.job_id}.heartbeat"


def touch_exec_heartbeat(job: ExecJob) -> None:
    import time

    path = heartbeat_path(job)
    if path is None:
        return
    ensure_parent(path)
    path.write_text(str(time.time()), encoding="utf-8")
