"""SAGE API server entry point (FastAPI + uvicorn).

Mounts ``/data``, ``/report``, ``/tool``, ``/secret``, and ``/admin/*`` routers.
Loads ``.env``, configures logging, and serves OpenAPI at ``/docs``.
"""

import asyncio
import logging
import warnings
import os
import sys

from dotenv import load_dotenv, find_dotenv
from starlette.routing import Mount

import cfg

from sage.logg import configure_console_utf8

configure_console_utf8()

from sage.logg import install_logging, info

install_logging()

from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
import uvicorn

from routers import data, report, tool, secret, admin_auth, admin_code, admin_user, admin_org
from sage.auth import announce_auth_mode, auth_enabled, verify_api_key
from sage.serve import shutdown_sage_resources

logging.getLogger("mcp.client.streamable_http").setLevel(logging.CRITICAL)
logging.getLogger("anyio").setLevel(logging.CRITICAL)

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.ERROR)

# --- FastAPI 앱 설정 ---
api = FastAPI(
    title="SAGE API Server",
    dependencies=[Depends(verify_api_key)],
)


def _custom_openapi():
    if api.openapi_schema:
        return api.openapi_schema
    schema = get_openapi(
        title=api.title,
        version=getattr(api, "version", "0.1.0"),
        routes=api.routes,
    )
    if auth_enabled():
        schema.setdefault("components", {}).setdefault(
            "securitySchemes",
            {
                "APIKeyHeader": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "API-Key",
                    "description": "SAGE_API_KEY from .env",
                }
            },
        )
        schema["security"] = [{"APIKeyHeader": []}]
    api.openapi_schema = schema
    return schema


api.openapi = _custom_openapi

# .env + NARRATIX_HOME → sys.path (외부 패키지·동일 루트 import 용)
try:
    load_dotenv(find_dotenv())

    narratix_home = os.environ.get('NARRATIX_HOME')
    if narratix_home and narratix_home not in sys.path:
        sys.path.insert(0, narratix_home)
except Exception as e:
    print(f"Env setup warning: {e}")

from multiprocessing import Process


def _resolve_bind() -> tuple[str, int]:
    from sage.serve import parse_uvicorn_bind

    cli_host, cli_port = parse_uvicorn_bind()
    return cli_host or cfg.host, cli_port if cli_port is not None else cfg.port


SAGE_HOST, SAGE_PORT = _resolve_bind()


def _bootstrap_if_uvicorn_cli() -> None:
    """python -m uvicorn main:app … — import 시점에 기존 8090/8091 점유 프로세스 정리."""
    from sage.serve import bootstrap_sage_ports, launched_via_uvicorn

    if __name__ == "__main__" or not launched_via_uvicorn():
        return
    global SAGE_HOST, SAGE_PORT
    SAGE_HOST, SAGE_PORT = bootstrap_sage_ports(cfg.host, cfg.port, announce=True)


_bootstrap_if_uvicorn_cli()


@api.on_event("startup")
async def prepare_sage_ports():
    """uvicorn 0.36+: lifespan startup → socket bind 순. bind 직전 포트 재확보."""
    from sage.serve import ensure_sage_ports

    announce_auth_mode()
    ensure_sage_ports(SAGE_HOST, SAGE_PORT, announce=True)


@api.on_event("shutdown")
async def shutdown_sage():
    shutdown_sage_resources()


@api.on_event("startup")
async def trigger_mcp():
    """MCP HTTP 게이트웨이(8091)를 별도 프로세스로 기동 — API 블로킹 방지."""
    from multiprocessing import Queue
    from sage.mcp import announce_mcp_when_ready, run_mcp_server

    ready_queue: Queue[str] = Queue()
    p = Process(
        target=run_mcp_server,
        args=(cfg.sage_mcp_bind_host, SAGE_PORT, ready_queue),
        daemon=True,
    )
    p.start()
    api.state.mcp_process = p

    asyncio.create_task(announce_mcp_when_ready(ready_queue))

    if cfg.sage_exec_driver == "docker_pool":
        asyncio.create_task(_warmup_exec_pool())


async def _warmup_exec_pool() -> None:
    """SAGE API startup — exec worker restart (host 코드 ↔ daemon 동기)."""
    from sage.exec.drivers.docker_pool import get_pool
    from sage.logg import error, warning

    pool = get_pool()
    try:
        await pool.restart_workers()
    except Exception as exc:
        warning(f"Exec pool restart 실패 — ensure_pool fallback: {exc}")
        try:
            await pool.ensure_pool()
        except Exception as fallback_exc:
            error(f"Exec pool 기동 실패: {fallback_exc}")
            raise


@api.get('/', tags=['default'])
async def greet(name: str = "User"):
    """MCP 서버 작동 확인용 인사 도구"""
    return f"Hello, {name}! SAGE MCP is running."


api.include_router(data.router)
api.include_router(report.router)
api.include_router(tool.router)
api.include_router(secret.router)
api.include_router(admin_auth.router)
api.include_router(admin_code.router)
api.include_router(admin_user.router)
api.include_router(admin_org.router)

app = api

DEV_RELOAD_EXCLUDES = (
    # codegen/run 중 대용량 산출물 변경으로 dev 서버가 재시작되지 않도록 제외
    cfg.root_path / "reports",
    cfg.root_path / "data",
    cfg.root_path / "dump",
)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="SAGE API server")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="개발 모드: auto-reload (reports/data/dump 제외)",
    )
    args = parser.parse_args()

    from sage.serve import bootstrap_sage_ports, run_sage_uvicorn

    host, port = bootstrap_sage_ports(cfg.host, cfg.port, announce=True)

    run_sage_uvicorn(
        app,
        host=host,
        port=port,
        reload=args.reload,
        reload_excludes=[str(p) for p in DEV_RELOAD_EXCLUDES],
    )
