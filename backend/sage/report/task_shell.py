"""Report task executor shell — prelude 파일 + LLM body.

LLM 은 ``async def run_task(...)`` 와 helper 만 생성한다.
import 는 ``task_prelude.py`` 단일 파일에서 읽어 조립한다 (문자열 tuple·regex 주입 금지).
"""

from __future__ import annotations

import ast
from pathlib import Path
from textwrap import dedent

BODY_MARKER = "# --- sage task body ---"
_PRELUDE_PATH = Path(__file__).with_name("task_prelude.py")


def codegen_syntax_hint(code: str) -> str:
    """release embed 등 흔한 syntax 실패 → validator 재시도용 안내."""
    if "apply_upstream_source_updates" in code or '"""' in code or "'''" in code:
        from sage.report.release_contract import MSG_PATCH_REQUIRED

        return MSG_PATCH_REQUIRED
    return ""


def prelude_path() -> Path:
    return _PRELUDE_PATH


def _prelude_text() -> str:
    return _PRELUDE_PATH.read_text(encoding="utf-8").strip()


def prelude_symbols() -> list[str]:
    """prelude AST 에서 주입 심볼 이름 목록 (프롬pt 계약용)."""
    tree = ast.parse(_prelude_text())
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.append(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.asname or alias.name.split(".")[0])
    return names


def split_task_source(code: str) -> tuple[str | None, str]:
    if BODY_MARKER in code:
        _, body = code.split(BODY_MARKER, 1)
        return _prelude_text(), body.lstrip("\n")
    return None, code


def extract_task_body(code: str) -> str:
    _, raw = split_task_source(code)
    try:
        tree = ast.parse(raw)
    except SyntaxError as exc:
        hint = codegen_syntax_hint(raw)
        msg = str(exc.msg or exc)
        if hint:
            raise ValueError(f"{msg} — {hint}") from exc
        raise ValueError(msg) from exc
    kept: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        kept.append(node)
    if not any(isinstance(n, ast.AsyncFunctionDef) and n.name == "run_task" for n in kept):
        raise ValueError(
            "async def run_task(task, ctx, reporter=None) 가 필요합니다 — "
            "import 없이 run_task 본문만 생성하세요."
        )
    module = ast.Module(body=kept, type_ignores=[])
    return ast.unparse(module).strip() + "\n"


def assemble_task_source(body: str) -> str:
    body = extract_task_body(body)
    return f"{_prelude_text()}\n{BODY_MARKER}\n\n{body}"


def assert_no_imports(code: str, *, where: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError(
                f"{where} import 금지 — {prelude_path().name} 가 runtime 에 주입됩니다. "
                "async def run_task(...) 와 helper 함수만 작성하세요."
            )


def assert_assembled(code: str) -> None:
    prelude, body = split_task_source(code)
    if prelude is None:
        raise ValueError(f"assembled task source 형식 아님 — {BODY_MARKER!r} marker 필요")
    if prelude.strip() != _prelude_text().strip():
        raise ValueError(
            f"task prelude 가 {prelude_path().name} 와 다릅니다 — 수동 편집 금지"
        )
    assert_no_imports(body, where="task body")


def runtime_contract_for_prompt() -> str:
    symbols = ", ".join(prelude_symbols())
    return dedent(
        f"""
        ## executor import 금지 (runtime prelude)
        - **import 문을 작성하지 마세요.** ``run_task`` 와 helper 함수만 출력합니다.
        - 실행 시 ``{prelude_path().name}`` 가 주입하는 심볼: {symbols}.
        - ``async def run_task(task, ctx, reporter=None):`` 시그니처 필수.
        """
    ).strip()
