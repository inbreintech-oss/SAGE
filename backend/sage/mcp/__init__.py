"""MCP gateway — tool client, server process, spec loading."""

from sage.mcp.client import (
    TOOL_BASE_PATH,
    call,
    close_all_sessions,
    convert_numpy_types,
    create_app,
    get_client,
    get_transport_path,
    load_mcp_from_path,
    load_tools_spec,
    mcp_loaded_message,
    tool_specs_for_llm,
    universal_serializer,
)
from sage.mcp.server import announce_mcp_when_ready, run_mcp_server

__all__ = [
    "TOOL_BASE_PATH",
    "announce_mcp_when_ready",
    "call",
    "close_all_sessions",
    "convert_numpy_types",
    "create_app",
    "get_client",
    "get_transport_path",
    "load_mcp_from_path",
    "load_tools_spec",
    "mcp_loaded_message",
    "run_mcp_server",
    "tool_specs_for_llm",
    "universal_serializer",
]
