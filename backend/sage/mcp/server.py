"""MCP uvicorn — main.py import 없이 별도 프로세스에서 실행 (Windows spawn)."""

from __future__ import annotations

import asyncio
import os
import sys
import warnings
from multiprocessing import Queue
from typing import TYPE_CHECKING

warnings.filterwarnings("ignore", category=DeprecationWarning)

if TYPE_CHECKING:
    from multiprocessing.queues import Queue as QueueType


async def announce_mcp_when_ready(
        ready_queue: QueueType[str],
        *,
        timeout_sec: float = 120.0,
) -> None:
    """MCP 자식이 도구 로드·lifespan 완료 후 보낸 메시지를 부모 콘솔에 출력."""
    from sage.serve.server import _announce

    try:
        msg = await asyncio.wait_for(asyncio.to_thread(ready_queue.get), timeout=timeout_sec)
    except asyncio.TimeoutError:
        return
    _announce(f"INFO:     {msg}")


def run_mcp_server(host: str, api_port: int, ready_queue: QueueType[str] | None = None) -> None:
    try:
        from sage.logg import install_logging
        from sage.serve.server import free_port

        install_logging()
        os.environ["MCP_REQUEST_TIMEOUT"] = "600"
        os.environ["MCP_SERVER_TIMEOUT"] = "600"

        mcp_port = api_port + 1
        free_port(mcp_port)

        import uvicorn

        from sage.mcp.client import create_app

        mcp_app = create_app(host=host, port=mcp_port)
        if ready_queue is not None:
            mcp_app.state.ready_queue = ready_queue

        config = uvicorn.Config(
            mcp_app,
            host=host,
            port=mcp_port,
            log_level="error",
            loop="asyncio",
            timeout_keep_alive=600,
            timeout_graceful_shutdown=60,
            limit_concurrency=500,
            backlog=4096,
            http="httptools",
        )
        server = uvicorn.Server(config)

        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(server.serve())
    except KeyboardInterrupt:
        pass