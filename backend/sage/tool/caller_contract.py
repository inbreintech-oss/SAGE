"""caller.py 계약 — import sage.mcp.call, kwargs 로 call 주입 금지."""

from __future__ import annotations

import ast
import re
import traceback
from typing import Any

_KWARGS_CALL_ASSIGN = re.compile(
    r'^[ \t]*call\s*=\s*kwargs\s*\[\s*[\'"]call[\'"]\s*\][ \t]*(#.*)?\s*$',
    re.M,
)
_KWARGS_CALL_GET = re.compile(
    r'^[ \t]*call\s*=\s*kwargs\.get\(\s*[\'"]call[\'"][^)]*\)[ \t]*(#.*)?\s*$',
    re.M,
)


def caller_source_normalized(source: str) -> str:
    return "\n".join(ln.rstrip() for ln in (source or "").strip().splitlines() if ln.strip())


def rewrite_kwargs_call_injection(source: str) -> str:
    """`call = kwargs['call']` 을 제거하고 `from sage.mcp import call` 을 보장."""
    text = source or ""
    stripped = _KWARGS_CALL_ASSIGN.sub("", text)
    stripped = _KWARGS_CALL_GET.sub("", stripped)
    if stripped == text:
        return text
    if "from sage.mcp import call" not in stripped and re.search(r"\bcall\s*\(", stripped):
        stripped = "from sage.mcp import call\n" + stripped.lstrip()
    return stripped


def assert_caller_mcp_import(source: str) -> None:
    """docker caller 계약. 위반 시 ValueError — LLM 재시도 메시지로 쓴다."""
    src = source or ""
    if not src.strip():
        raise ValueError("검증할 caller 소스코드가 존재하지 않습니다.")
    tree = ast.parse(src)
    has_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "") == "sage.mcp":
            if any(alias.name == "call" for alias in node.names):
                has_import = True
        if isinstance(node, ast.Subscript):
            sl = node.slice
            key = sl.value if isinstance(sl, ast.Constant) else None
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "kwargs"
                and key == "call"
            ):
                raise ValueError(
                    "계약 위반: `kwargs['call']` 금지. "
                    "`from sage.mcp import call` 후 `await call(path, name, args)` 를 사용하라. "
                    "도커 워커는 call 함수를 인자로 넘기지 않는다."
                )
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "kwargs"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "call"
        ):
            raise ValueError(
                "계약 위반: `kwargs.get('call')` 금지. "
                "`from sage.mcp import call` 후 `await call(...)` 를 사용하라."
            )
    uses_call = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "call"
        for n in ast.walk(tree)
    )
    if uses_call and not has_import:
        raise ValueError(
            "계약 위반: `await call(...)` 앞에 `from sage.mcp import call` 이 없다. "
            "kwargs 로 함수를 받지 말 것."
        )


def format_exec_error_for_sourcefix(exc: BaseException) -> str:
    """SourceFix user prompt 용 — 원인 한 줄을 맨 앞에. traceback 은 뒤에 짧게."""
    from sage.nodes.lesson_learn import compress_error_for_lesson

    tb = traceback.format_exc()
    root = compress_error_for_lesson(tb) or f"{type(exc).__name__}: {exc}"
    loc: list[str] = []
    for ln in tb.splitlines():
        s = ln.strip()
        if "caller.py" in s or s.startswith("call = kwargs") or "kwargs[\"call\"]" in s or "kwargs['call']" in s:
            loc.append(s)
    hint = ""
    blob = tb + str(exc)
    if "KeyError: 'call'" in blob or "kwargs[\"call\"]" in blob or "kwargs['call']" in blob:
        hint = (
            "원인: 워커는 call 을 kwargs 로 넘기지 않는다. "
            "`call = kwargs['call']` 을 지우고 `from sage.mcp import call` 을 넣어라."
        )
    parts = [
        "【반드시 이 오류를 고친다 — 원본 코드를 그대로 반환하면 같은 오류가 난다】",
        root,
        hint,
    ]
    if loc:
        parts.append("위치:\n" + "\n".join(loc[:8]))
    tail = tb.strip()
    if len(tail) > 1600:
        tail = tail[-1600:]
    parts.append("traceback:\n" + tail)
    return "\n".join(p for p in parts if p).strip()


def caller_source_of(data: Any) -> str:
    for attr in ("caller", "fixed_code", "code"):
        val = getattr(data, attr, None)
        if isinstance(val, str) and val.strip():
            return val
    return ""
