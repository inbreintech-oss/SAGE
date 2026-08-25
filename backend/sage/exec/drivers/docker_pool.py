"""Docker warm pool — idle worker에 job dispatch, 완료는 result 파일로 확인."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
import urllib.error
from dataclasses import dataclass
from pathlib import Path

import cfg
from sage.exec.http_util import request_json
from sage.exec.jobs import translate_job_for_container
from sage.exec.models import ExecJob, ExecResult, heartbeat_path, write_result_file
from sage.logg import info, warning


@dataclass
class PoolSlot:
    container_id: str
    name: str
    host: str
    port: int = 9000
    status: str = "idle"
    jobs_run: int = 0


class ExecPool:
    """Host-side pool — compose로 worker 기동, slot acquire/release."""

    def __init__(self) -> None:
        self._slots: list[PoolSlot] = []
        self._lock = asyncio.Lock()
        self._init_lock = asyncio.Lock()
        self._initialized = False
        self._compose_file = Path(cfg.root_path) / "docker-compose.exec.yml"

    def _docker_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.setdefault("NARRATIX_HOME", str(Path(cfg.root_path).resolve()))
        return env

    async def _run_docker(self, *args: str, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
        return await asyncio.to_thread(
            subprocess.run,
            ["docker", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env=self._docker_env(),
        )

    async def restart_workers(self) -> None:
        """SAGE API startup — stale daemon import cache 방지 (main.py ↔ exec pool 동기)."""
        async with self._init_lock:
            if not self._compose_file.is_file():
                raise RuntimeError(f"docker-compose.exec.yml 없음: {self._compose_file}")

            await self._refresh_slots()
            if self._slots:
                info("Exec pool restart — SAGE API startup (worker code reload)")
                proc = await self._run_docker(
                    "compose", "-f", str(self._compose_file), "restart", timeout=180.0
                )
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"exec pool restart 실패: {proc.stderr or proc.stdout}"
                    )
            else:
                info("Exec pool 기동 — worker 없음, compose up")
                proc = await self._run_docker(
                    "compose", "-f", str(self._compose_file), "up", "-d", timeout=180.0
                )
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"exec pool compose 실패: {proc.stderr or proc.stdout}"
                    )

            self._slots = []
            self._initialized = False
            await self._wait_pool_ready(timeout_sec=90.0)
            self._initialized = True
            info(f"Exec pool ready — {len(self._slots)} worker(s)")

    async def ensure_pool(self) -> None:
        async with self._init_lock:
            if self._initialized:
                return
            if not self._compose_file.is_file():
                raise RuntimeError(f"docker-compose.exec.yml 없음: {self._compose_file}")

            info("Exec pool 기동 — docker compose up (project: n2-exec)")
            proc = await self._run_docker(
                "compose", "-f", str(self._compose_file), "up", "-d", timeout=180.0
            )
            if proc.returncode != 0:
                raise RuntimeError(f"exec pool compose 실패: {proc.stderr or proc.stdout}")

            await self._wait_pool_ready(timeout_sec=90.0)
            self._initialized = True
            info(f"Exec pool ready — {len(self._slots)} worker(s)")

    async def _wait_pool_ready(self, *, timeout_sec: float) -> None:
        deadline = time.monotonic() + timeout_sec
        last_err = "worker 없음"
        while time.monotonic() < deadline:
            await self._refresh_slots()
            if not self._slots:
                await asyncio.sleep(1.0)
                continue
            unhealthy: list[str] = []
            for slot in self._slots:
                ok, err = await self._check_health(slot)
                if not ok:
                    unhealthy.append(f"{slot.name}: {err}")
            if not unhealthy:
                return
            last_err = "; ".join(unhealthy)
            await asyncio.sleep(1.0)
        raise RuntimeError(f"exec pool health check timeout — {last_err}")

    async def _check_health(self, slot: PoolSlot) -> tuple[bool, str]:
        url = self._slot_url(slot, "/health")
        try:
            code, body = await request_json("GET", url, timeout_sec=5.0)
            if code == 200:
                return True, ""
            return False, f"HTTP {code}: {body}"
        except Exception as exc:
            return False, str(exc)

    async def _refresh_slots(self) -> None:
        proc = await self._run_docker(
            "ps",
            "--filter", "label=sage.exec.role=worker",
            "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}",
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or "docker ps failed")

        slots: list[PoolSlot] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            cid, name = parts[0], parts[1]
            host, port = await self._resolve_slot_endpoint(cid, name)
            existing = next((s for s in self._slots if s.container_id == cid), None)
            jobs_run = existing.jobs_run if existing else 0
            status = existing.status if existing and existing.status == "busy" else "idle"
            slots.append(
                PoolSlot(
                    container_id=cid,
                    name=name,
                    host=host,
                    port=port,
                    status=status,
                    jobs_run=jobs_run,
                )
            )
        self._slots = slots

    async def _resolve_slot_endpoint(self, container_id: str, name: str) -> tuple[str, int]:
        proc = await self._run_docker(
            "inspect", "-f",
            "{{if (index .NetworkSettings.Ports \"9000/tcp\")}}"
            "{{(index (index .NetworkSettings.Ports \"9000/tcp\") 0).HostPort}}"
            "{{end}}",
            container_id,
        )
        host_port = (proc.stdout or "").strip()
        if host_port.isdigit():
            return "127.0.0.1", int(host_port)

        proc = await self._run_docker(
            "inspect", "-f",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            container_id,
        )
        ip = (proc.stdout or "").strip()
        if ip:
            warning(
                f"exec worker {name} — publish port 없음, bridge IP 사용 ({ip}:9000). "
                "Windows 에서는 docker-compose.exec.yml ports(9001/9002) 확인"
            )
            return ip, 9000
        raise RuntimeError(f"worker endpoint 없음: {name} ({container_id})")

    async def acquire(self, timeout_sec: float | None = None) -> PoolSlot:
        timeout = timeout_sec or cfg.sage_exec_pool_acquire_sec
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            async with self._lock:
                await self._refresh_slots()
                for slot in self._slots:
                    if slot.status != "idle":
                        continue
                    ok, err = await self._check_health(slot)
                    if not ok:
                        warning(f"exec slot unhealthy — skip {slot.name}: {err}")
                        continue
                    slot.status = "busy"
                    return slot
            await asyncio.sleep(0.2)
        raise TimeoutError(f"exec pool acquire timeout ({timeout}s)")

    async def release(
        self,
        slot: PoolSlot,
        *,
        force_recycle: bool = False,
        dispatch_failed: bool = False,
    ) -> None:
        async with self._lock:
            if dispatch_failed:
                await self._recycle_slot(slot)
                return

            slot.jobs_run += 1
            if force_recycle or slot.jobs_run >= cfg.sage_exec_max_jobs_per_container:
                await self._recycle_slot(slot)
                return

            try:
                url = self._slot_url(slot, "/reset")
                code, _ = await request_json("POST", url, timeout_sec=10.0)
                if code >= 400:
                    warning(f"exec slot reset HTTP {code} — {slot.name} idle without recycle")
                slot.status = "idle"
            except Exception as exc:
                ok, health_err = await self._check_health(slot)
                if ok:
                    warning(
                        f"exec slot reset failed — {slot.name}: {exc}; "
                        "health OK — idle without recycle"
                    )
                    slot.status = "idle"
                else:
                    warning(
                        f"exec slot reset+health failed — {slot.name}: "
                        f"reset={exc}, health={health_err}; recycling"
                    )
                    await self._recycle_slot(slot)

    async def _recycle_slot(self, slot: PoolSlot) -> None:
        warning(f"Exec pool recycle: {slot.name} (jobs={slot.jobs_run})")
        await self._run_docker("rm", "-f", slot.container_id, timeout=30.0)
        proc = await self._run_docker(
            "compose", "-f", str(self._compose_file), "up", "-d", timeout=120.0
        )
        if proc.returncode != 0:
            raise RuntimeError(f"exec pool recreate 실패: {proc.stderr or proc.stdout}")
        await self._wait_pool_ready(timeout_sec=90.0)

    def _slot_url(self, slot: PoolSlot, path: str) -> str:
        return f"http://{slot.host}:{slot.port}{path}"

    def _read_result_file(self, job: ExecJob) -> ExecResult | None:
        if not job.result_file:
            return None
        path = Path(job.result_file)
        if not path.is_file():
            return None
        try:
            parsed = ExecResult.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if parsed.job_id == job.job_id:
                return parsed
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass
        return None

    async def _fetch_daemon_result(self, slot: PoolSlot, job_id: str) -> ExecResult | None:
        """Stall 시 one-shot — poll loop 아님."""
        url = self._slot_url(slot, f"/exec/{job_id}")
        try:
            code, body = await request_json("GET", url, timeout_sec=5.0)
            if code != 200 or not isinstance(body, dict):
                return None
            raw = body.get("result")
            if not isinstance(raw, dict):
                return None
            parsed = ExecResult.from_dict(raw)
            if parsed.job_id == job_id:
                return parsed
        except Exception:
            pass
        return None

    async def _wait_for_result_file(self, job: ExecJob, slot: PoolSlot | None = None) -> ExecResult:
        if not job.result_file:
            raise RuntimeError(f"ExecJob.result_file required (job={job.job_id})")

        stall_sec = max(5, cfg.sage_exec_stall_sec)
        deadline = time.monotonic() + job.limits.timeout_sec
        started = time.monotonic()
        progress_path = Path(job.progress_file) if job.progress_file else None
        heartbeat = heartbeat_path(job)
        last_activity_mtime: float | None = None

        while time.monotonic() < deadline:
            result = self._read_result_file(job)
            if result is not None:
                return result

            now = time.monotonic()
            for probe in (progress_path, heartbeat):
                if probe and probe.is_file():
                    last_activity_mtime = probe.stat().st_mtime
                    break
            if last_activity_mtime is not None:
                pass
            elif now - started >= stall_sec:
                fallback = await self._fetch_daemon_result(slot, job.job_id) if slot else None
                if fallback is not None:
                    write_result_file(job.result_file, fallback)
                    return fallback
                return ExecResult(
                    ok=False,
                    job_id=job.job_id,
                    error=(
                        f"exec stall ({stall_sec}s) — worker produced no progress/result "
                        f"(job={job.job_id})"
                    ),
                    exit_code=125,
                )
            elif (
                last_activity_mtime is not None
                and time.time() - last_activity_mtime >= stall_sec
            ):
                fallback = await self._fetch_daemon_result(slot, job.job_id) if slot else None
                if fallback is not None:
                    write_result_file(job.result_file, fallback)
                    return fallback
                return ExecResult(
                    ok=False,
                    job_id=job.job_id,
                    error=(
                        f"exec stall ({stall_sec}s) — progress stopped "
                        f"(job={job.job_id})"
                    ),
                    exit_code=125,
                )

            await asyncio.sleep(0.15)

        return ExecResult(
            ok=False,
            job_id=job.job_id,
            error=f"exec timeout ({job.limits.timeout_sec}s) — result file missing",
            exit_code=124,
        )

    async def run_job(self, job: ExecJob) -> ExecResult:
        await self.ensure_pool()
        slot = await self.acquire()
        info(
            f"[exec:docker_pool] slot={slot.name} {slot.host}:{slot.port} "
            f"kind={job.kind} job_id={job.job_id}"
        )

        container_job = translate_job_for_container(job)
        result: ExecResult | None = None
        dispatch_accepted = False

        try:
            url = self._slot_url(slot, "/exec")
            code, body = await request_json(
                "POST", url, body=container_job.to_dict(), timeout_sec=60.0
            )
            if code >= 400:
                raise RuntimeError(f"daemon /exec HTTP {code}: {body}")

            dispatch_accepted = True
            result = await self._wait_for_result_file(job, slot=slot)
            return result

        except Exception:
            recovered = self._read_result_file(job)
            if recovered is not None:
                return recovered
            raise

        finally:
            dispatch_failed = not dispatch_accepted
            recycle = bool(
                result
                and not result.ok
                and result.exit_code not in (124, 125)
            )
            await self.release(
                slot,
                force_recycle=recycle,
                dispatch_failed=dispatch_failed,
            )


_pool: ExecPool | None = None


def get_pool() -> ExecPool:
    global _pool
    if _pool is None:
        _pool = ExecPool()
    return _pool


def reset_pool() -> None:
    global _pool
    _pool = None


async def run_docker_pool(job: ExecJob) -> ExecResult:
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            return await get_pool().run_job(job)
        except (TimeoutError, OSError, urllib.error.URLError, RuntimeError) as exc:
            last_exc = exc
            reset_pool()
            if attempt == 0:
                warning(f"docker_pool transient error — pool reset 후 재시도: {exc}")
                await asyncio.sleep(1.5)
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("docker_pool run failed")
