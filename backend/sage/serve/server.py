"""로컬 dev 서버 — 포트 점유 프로세스 정리·재시작."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import time

logger = logging.getLogger("sage.server")

_PORT_IN_USE_MSG = (
    "포트 사용 중입니다. 자동으로 포트 사용 프로세스를 종료하고 서버를 시작합니다."
)
_PORT_READY_MSG = "포트 확보 완료. SAGE 서버를 시작합니다."

def _skip_port_kill() -> bool:
    return os.environ.get("SAGE_SKIP_PORT_KILL", "").lower() in ("1", "true", "yes")

def launched_via_uvicorn() -> bool:
    if not sys.argv:
        return False
    prog = os.path.basename(sys.argv[0]).lower()
    if prog in ("uvicorn", "uvicorn.exe"):
        return True
    argv = sys.argv[1:]
    if "-m" in argv and "uvicorn" in argv:
        return True
    return "uvicorn" in argv

def should_auto_free_ports(*, importing_main: bool = False) -> bool:
    if _skip_port_kill():
        return False
    if importing_main and launched_via_uvicorn():
        return True
    if __name__ == "__main__":
        return True
    return False

def bootstrap_sage_ports(
    default_host: str,
    default_port: int,
    *,
    announce: bool = True,
) -> tuple[str, int]:
    """기동 전 8090·8091 포트 점유 프로세스 종료.

    - ``python main.py`` — __main__ 에서 호출
    - ``python -m uvicorn main:app --host … --port …`` — main import 시 호출
    CLI ``--host`` / ``--port`` 가 있으면 우선, 없으면 default 사용.
    """
    if _skip_port_kill():
        cli_host, cli_port = parse_uvicorn_bind()
        return cli_host or default_host, cli_port if cli_port is not None else default_port

    cli_host, cli_port = parse_uvicorn_bind()
    host = cli_host or default_host
    port = cli_port if cli_port is not None else default_port
    ensure_sage_ports(host, port, announce=announce)
    return host, port

def parse_uvicorn_bind(argv: list[str] | None = None) -> tuple[str | None, int | None]:
    """sys.argv 에서 --host / --port (없으면 None)."""
    argv = argv if argv is not None else sys.argv
    host: str | None = None
    port: int | None = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--host", "-h") and i + 1 < len(argv):
            host = argv[i + 1]
            i += 2
            continue
        if arg.startswith("--host="):
            host = arg.split("=", 1)[1]
            i += 1
            continue
        if arg in ("--port", "-p") and i + 1 < len(argv):
            port = int(argv[i + 1])
            i += 2
            continue
        if arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
            i += 1
            continue
        i += 1
    return host, port

def _pids_listening_on_port(port: int) -> set[int]:
    if sys.platform == "win32":
        return _pids_listening_on_port_windows(port)
    return _pids_listening_on_port_unix(port)

def _pids_listening_on_port_windows(port: int) -> set[int]:
    try:
        proc = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return set()
    pids: set[int] = set()
    needle = f":{port}"
    for line in proc.stdout.splitlines():
        upper = line.upper()
        if "LISTENING" not in upper:
            continue
        if needle not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pids.add(int(parts[-1]))
        except ValueError:
            continue
    return pids

def _pids_listening_on_port_unix(port: int) -> set[int]:
    for cmd in (
        ["ss", "-ltnp", f"sport = :{port}"],
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
    ):
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError:
            continue
        if proc.returncode != 0 and not proc.stdout.strip():
            continue
        pids: set[int] = set()
        for line in proc.stdout.splitlines():
            if sys.platform != "win32" and cmd[0] == "lsof":
                parts = line.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    pids.add(int(parts[1]))
                continue
            for match in re.finditer(r"pid=(\d+)", line):
                pids.add(int(match.group(1)))
        if pids:
            return pids
    return set()

def _foreign_pids_on_port(port: int) -> set[int]:
    pids = _pids_listening_on_port(port)
    pids.discard(os.getpid())
    return pids

def ports_in_use(*ports: int) -> dict[int, set[int]]:
    out: dict[int, set[int]] = {}
    for port in ports:
        pids = _foreign_pids_on_port(port)
        if pids:
            out[port] = pids
    return out

def port_is_free(port: int) -> bool:
    return not _foreign_pids_on_port(port)

def _announce(msg: str) -> None:
    try:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    except Exception:
        print(msg.encode("utf-8", errors="replace").decode("utf-8", errors="replace"), flush=True)

def _kill_pid(pid: int) -> bool:
    if pid <= 0 or pid == os.getpid():
        return False
    try:
        if sys.platform == "win32":
            proc = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            return proc.returncode == 0
        proc = subprocess.run(
            ["kill", "-9", str(pid)],
            capture_output=True,
            check=False,
        )
        return proc.returncode == 0
    except OSError:
        return False

def free_port(port: int, *, wait_sec: float | None = None, retries: int = 6) -> list[int]:
    if wait_sec is None:
        wait_sec = 1.2 if sys.platform == "win32" else 0.8
    killed: list[int] = []
    for attempt in range(retries):
        pids = _foreign_pids_on_port(port)
        if not pids:
            break
        for pid in sorted(pids):
            if _kill_pid(pid):
                killed.append(pid)
                logger.warning("포트 %s 점유 프로세스 종료: PID %s", port, pid)
        if attempt < retries - 1:
            time.sleep(wait_sec)
    if killed:
        time.sleep(wait_sec)
    return killed

def free_ports(*ports: int, wait_sec: float = 0.8) -> dict[int, list[int]]:
    seen: set[int] = set()
    result: dict[int, list[int]] = {}
    for port in ports:
        if port in seen:
            continue
        seen.add(port)
        result[port] = free_port(port, wait_sec=wait_sec)
    return result

def ensure_sage_ports(
    host: str,
    api_port: int,
    *,
    include_mcp: bool = True,
    announce: bool = True,
) -> dict[int, list[int]]:
    port_list = [api_port, api_port + 1] if include_mcp else [api_port]
    occupied = ports_in_use(*port_list)

    if occupied and announce:
        detail = ", ".join(
            f"{p}(PID {','.join(map(str, sorted(pids)))})"
            for p, pids in sorted(occupied.items())
        )
        _announce(f"{_PORT_IN_USE_MSG} [{host}: {detail}]")

    freed = free_ports(*port_list)

    still_occupied = ports_in_use(*port_list)
    if still_occupied:
        freed = free_ports(*port_list)
        still_occupied = ports_in_use(*port_list)

    if still_occupied and announce:
        detail = ", ".join(
            f"{p}(PID {','.join(map(str, sorted(pids)))})"
            for p, pids in sorted(still_occupied.items())
        )
        _announce(f"포트 확보 실패 — 아직 사용 중: [{host}: {detail}]")

    if occupied and announce and not still_occupied:
        summary = ", ".join(f"{p}->{pids or '-'}" for p, pids in sorted(freed.items()))
        _announce(f"{_PORT_READY_MSG} (API {api_port}, MCP {api_port + 1}) - {summary}")
        try:
            from sage.logg import info

            info(f"포트 정리 ({host}): {summary}")
        except Exception:
            pass

    return freed


def shutdown_sage_resources() -> None:
    """Ctrl+C·프로세스 종료 시 DB·MCP 자식 프로세스 정리."""
    try:
        from sage.db import saged

        saged.close()
    except Exception:
        pass
    try:
        from sage.llm.llms import shutdown_llm_executor

        shutdown_llm_executor(wait=False)
    except Exception:
        pass
    try:
        from sage.db.store import _unregister_pymongo_atexit

        _unregister_pymongo_atexit()
    except Exception:
        pass
    try:
        import multiprocessing as mp

        for p in mp.active_children():
            if p.is_alive():
                p.terminate()
            p.join(timeout=2)
    except Exception:
        pass


def run_sage_uvicorn(
    app,
    *,
    host: str,
    port: int,
    reload: bool = False,
    reload_excludes: list[str] | None = None,
) -> None:
    """포트 정리 후 uvicorn 기동. bind 실패 시 1회 재시도."""
    import uvicorn

    try:
        for attempt in range(2):
            ensure_sage_ports(host, port, announce=(attempt == 0))
            if not port_is_free(port):
                if attempt == 0:
                    _announce(f"포트 {port} 아직 사용 중 — 프로세스 종료 후 재시도합니다.")
                    free_port(port)
                    free_port(port + 1)
                    continue
                raise OSError(f"포트 {port} 를 확보하지 못했습니다.")

            try:
                if reload:
                    uvicorn.run(
                        "main:app",
                        host=host,
                        port=port,
                        reload=True,
                        reload_excludes=reload_excludes or [],
                    )
                else:
                    uvicorn.run(app, host=host, port=port)
                return
            except KeyboardInterrupt:
                _announce("SAGE 서버 종료")
                shutdown_sage_resources()
                return
            except OSError as exc:
                winerr = getattr(exc, "winerror", None)
                if attempt == 0 and (winerr == 10048 or winerr is None):
                    _announce(f"포트 {port} bind 실패 — 자동 종료 후 재시작합니다.")
                    free_port(port)
                    free_port(port + 1)
                    continue
                raise
    finally:
        shutdown_sage_resources()
