# custom_logger.py
import json
import logging
import logging.handlers
import sys
import os
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from fastapi.routing import APIRoute
from sse_starlette import EventSourceResponse
# from fastapi.sse import EventSourceResponse
from fastapi import Request, Response

import cfg

LOG_DIR = cfg.root_path / "logs"
REPORT_LOG_DIR = LOG_DIR / "report"
LOGGER_NAME = "sage"
LOG_FILE_NAME = os.path.join(LOG_DIR, f"{LOGGER_NAME}.log")
LOG_LEVEL = os.environ.get("LOG_LEVEL", logging.INFO)
LOG_FORMAT = "[%(asctime)s] (%(name)s) %(levelname)s: %(message)s"
CONSOLE_BRIEF_FORMAT = "[%(asctime)s] %(message)s"
CONSOLE_BRIEF_DATEFMT = "%H:%M:%S"

_logger = None
_console_utf8_configured = False
_uvicorn_logging_patched = False
_report_log_path: ContextVar[Optional[Path]] = ContextVar("report_log_path", default=None)


class _ConsoleBriefFilter(logging.Filter):
    """콘솔: SSE 요약·경고 이상·force_console 만."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "console_brief", False):
            return True
        if getattr(record, "force_console", False):
            return True
        return record.levelno >= logging.WARNING


class _FileDetailFilter(logging.Filter):
    """파일: console_brief 전용 레코드 제외 (상세 로그)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not getattr(record, "console_brief", False)


def configure_console_utf8() -> None:
    global _console_utf8_configured
    if _console_utf8_configured:
        return
    _console_utf8_configured = True

    os.environ.setdefault("PYTHONUTF8", "1")
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)
            kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _refresh_console_handlers() -> None:
    configure_console_utf8()
    targets = (
        ("", sys.stderr),
        ("uvicorn", sys.stderr),
        ("uvicorn.error", sys.stderr),
        ("uvicorn.access", sys.stdout),
        (LOGGER_NAME, sys.stdout),
    )
    for name, stream in targets:
        logger = logging.getLogger(name) if name else logging.getLogger()
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                    handler, logging.FileHandler
            ):
                handler.stream = stream


def _patch_uvicorn_configure_logging() -> None:
    global _uvicorn_logging_patched
    if _uvicorn_logging_patched:
        return
    _uvicorn_logging_patched = True

    import uvicorn.config as uvicorn_config

    original = uvicorn_config.Config.configure_logging

    def configure_logging(self):
        original(self)
        _refresh_console_handlers()

    uvicorn_config.Config.configure_logging = configure_logging


def install_logging() -> None:
    configure_console_utf8()
    _patch_uvicorn_configure_logging()
    _refresh_console_handlers()


def setup_logger(logger_name=LOGGER_NAME):
    global _logger

    configure_console_utf8()
    logger = logging.getLogger(logger_name)
    logger.propagate = False

    if logger.handlers:
        return logger

    logger.setLevel(LOG_LEVEL)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(REPORT_LOG_DIR, exist_ok=True)

    detail_formatter = logging.Formatter(LOG_FORMAT)
    brief_formatter = logging.Formatter(CONSOLE_BRIEF_FORMAT, datefmt=CONSOLE_BRIEF_DATEFMT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(brief_formatter)
    console_handler.addFilter(_ConsoleBriefFilter())
    logger.addHandler(console_handler)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_FILE_NAME,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setFormatter(detail_formatter)
    file_handler.addFilter(_FileDetailFilter())
    logger.addHandler(file_handler)

    _logger = logger
    return logger


def get_logger():
    if _logger is None:
        return setup_logger()
    return _logger


def file_log_uri(path: Path) -> str:
    """터미널(Cursor/VS Code)에서 클릭 가능한 file URI."""
    return path.resolve().as_uri()


def open_report_log(rid: str) -> Path:
    """리포트별 상세 로그 파일 — SSE 전체 기록."""
    path = REPORT_LOG_DIR / f"{rid}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# report log {rid} started {datetime.now().isoformat(timespec='seconds')}\n",
        encoding="utf-8",
    )
    _report_log_path.set(path)
    return path


def close_report_log() -> None:
    _report_log_path.set(None)


def append_report_log(line: str) -> None:
    path = _report_log_path.get()
    if path is None:
        return
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {line}\n")


def log_console_brief(message: str) -> None:
    get_logger().info(message, extra={"console_brief": True})


def log_report_log_link(rid: str, path: Path) -> None:
    uri = file_log_uri(path)
    log_console_brief(f"[report] 상세 로그 → {uri}")
    append_report_log(f"log file: {path}")


def _sse_msg_from_data(data) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return str(parsed.get("msg", data))
        except json.JSONDecodeError:
            return data
        return data
    if isinstance(data, dict):
        return str(data.get("msg", json.dumps(data, ensure_ascii=False)))
    return str(data)


def log_sse(event: Optional[str], data, *, detail: str) -> None:
    """콘솔: [event] msg / 파일·report.log: detail."""
    msg = _sse_msg_from_data(data)
    event_label = event or "?"
    log_console_brief(f"[{event_label}] {msg}")
    get_logger().info(detail)
    append_report_log(detail)


def debug(message, *args, **kwargs):
    get_logger().debug(message, *args, **kwargs)


def info(message, *args, **kwargs):
    get_logger().info(message, *args, **kwargs)


def warning(message, *args, **kwargs):
    kwargs.setdefault("extra", {})
    if "extra" in kwargs and isinstance(kwargs["extra"], dict):
        kwargs["extra"].setdefault("force_console", True)
    get_logger().warning(message, *args, **kwargs)


def trace(message, *args, **kwargs):
    kwargs["exc_info"] = kwargs.get("exc_info", True)
    kwargs.setdefault("extra", {"force_console": True})
    get_logger().error(message, *args, **kwargs)


def error(message, *args, **kwargs):
    kwargs.setdefault("extra", {"force_console": True})
    get_logger().error(message, *args, **kwargs)


def critical(message, *args, **kwargs):
    kwargs.setdefault("extra", {"force_console": True})
    get_logger().critical(message, *args, **kwargs)


class LoggingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            path = request.url.path
            method = request.method

            body = await request.body()
            if body:
                try:
                    payload = json.loads(body.decode("utf-8"))
                    info(
                        f"[{method}] {path} - Payload: {json.dumps(payload, ensure_ascii=False)}"
                    )
                except Exception:
                    pass

            response = await original_route_handler(request)

            if isinstance(response, EventSourceResponse):
                original_iterator = response.body_iterator

                async def logging_iterator():
                    async for chunk in original_iterator:
                        if isinstance(chunk, dict):
                            event = chunk.get("event")
                            data = chunk.get("data")

                            if isinstance(data, (dict, list)):
                                data_out = json.dumps(data, ensure_ascii=False)
                            else:
                                data_out = data

                            detail = f"[{method}] {path} - SSE: event={event!r} data={data_out!r}"
                            log_sse(event, data, detail=detail)
                            # EventSourceResponse 가 dict -> SSE bytes 로 인코딩한다.
                            # 여기서 문자열로 재포맷하면 wire 포맷이 깨져 클라이언트가 이벤트를 못 읽는다.
                            yield chunk
                        else:
                            text = str(chunk).strip()
                            if text:
                                info(f"[{method}] {path} - SSE chunk: {text[:500]}")
                            yield chunk

                response.body_iterator = logging_iterator()

            elif hasattr(response, "body"):
                try:
                    res_raw = response.body
                    log_data = (
                        json.loads(res_raw.decode("utf-8"))
                        if isinstance(res_raw, bytes)
                        else res_raw
                    )
                    info(
                        f"[{method}] {path} - Response: {json.dumps(log_data, ensure_ascii=False)}"
                    )
                except Exception:
                    pass

            return response

        return custom_route_handler
