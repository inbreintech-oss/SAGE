"""Tool codegen artifacts — dump, execute, fix loop (lazy exports)."""

from __future__ import annotations

_LAZY = {
    "dump",
    "dump_metadata",
    "execute",
    "execute_caller_with_fix",
    "execute_with_fix",
    "finalize_caller_source",
    "generate_tool_id",
    "resolve_id",
    "update_metadata",
}


def __getattr__(name: str):
    if name not in _LAZY:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from sage.tool import runtime as _runtime

    return getattr(_runtime, name)


__all__ = sorted(_LAZY)
