"""codegen AST — schema.py contract 검증 (report 레이어)."""

from __future__ import annotations

import ast
import re

from sage.data.schema_contract import SchemaContractError

_AST_TYPE_UNKNOWN = "unknown"
_AST_TYPE_CALL = "call"


def _annotation_compatible(expected: str, actual: str) -> bool:
    if actual in (_AST_TYPE_UNKNOWN, _AST_TYPE_CALL):
        return True
    if expected == actual:
        return True
    if expected == "float" and actual == "int":
        return True
    return False


def _infer_ast_type(node: ast.expr | None) -> str:
    if node is None:
        return _AST_TYPE_UNKNOWN
    if isinstance(node, ast.Constant):
        v = node.value
        if v is None:
            return _AST_TYPE_UNKNOWN
        if isinstance(v, bool):
            return "bool"
        if isinstance(v, int) and not isinstance(v, bool):
            return "int"
        if isinstance(v, float):
            return "float"
        if isinstance(v, str):
            s = v.strip()
            if re.match(r"^\d{8}$", s):
                return "int"
            if re.match(r"^\d{4}-\d{2}-\d{2}", s):
                return "date"
            return "str"
        return _AST_TYPE_UNKNOWN
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            name = func.id
            if name in ("int", "float", "str", "bool"):
                return name
            if name in ("parse_date", "date", "datetime"):
                return _AST_TYPE_CALL
        if isinstance(func, ast.Attribute):
            attr = func.attr
            if attr in ("strptime", "fromisoformat", "to_pydatetime", "strftime"):
                return _AST_TYPE_CALL
        return _AST_TYPE_CALL
    if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.IfExp, ast.Subscript, ast.Attribute)):
        return _AST_TYPE_CALL
    if isinstance(node, ast.Dict):
        return _AST_TYPE_UNKNOWN
    if isinstance(node, ast.List):
        return _AST_TYPE_UNKNOWN
    return _AST_TYPE_UNKNOWN


def _check_dict_literal(
    node: ast.Dict,
    model: str,
    field_types: dict[str, str],
    *,
    line: int,
) -> list[str]:
    issues: list[str] = []
    if not field_types:
        return issues
    for key_node, val_node in zip(node.keys, node.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
            continue
        field = key_node.value
        expected = field_types.get(field)
        if not expected:
            continue
        actual = _infer_ast_type(val_node)
        if actual == _AST_TYPE_CALL:
            issues.append(
                f"L{line}: {model}.{field} — schema `{expected}` 인데 "
                f"함수·변환 호출 사용 (API 값을 타입에 맞게 직접 매핑)"
            )
            continue
        if not _annotation_compatible(expected, actual):
            issues.append(
                f"L{line}: {model}.{field} — schema `{expected}` ≠ 정적 추론 `{actual}`"
            )
    return issues


def _extract_queue_update_calls(tree: ast.Module) -> list[tuple[int, str, ast.expr]]:
    calls: list[tuple[int, str, ast.expr]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "queue_update"):
            continue
        if len(node.args) < 2:
            continue
        model_arg = node.args[0]
        if not isinstance(model_arg, ast.Constant) or not isinstance(model_arg.value, str):
            continue
        calls.append((node.lineno, model_arg.value, node.args[1]))
    return calls


def validate_codegen_schema_contract(
    code: str,
    schema_fields: dict[str, dict[str, str]],
) -> None:
    if not schema_fields or "queue_update" not in code:
        return
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return

    issues: list[str] = []
    for line, model, records_arg in _extract_queue_update_calls(tree):
        field_types = schema_fields.get(model, {})
        if not field_types:
            continue
        if isinstance(records_arg, ast.List):
            for elt in records_arg.elts:
                if isinstance(elt, ast.Dict):
                    issues.extend(_check_dict_literal(elt, model, field_types, line=line))
        elif isinstance(records_arg, ast.Dict):
            issues.extend(_check_dict_literal(records_arg, model, field_types, line=line))

    if issues:
        raise SchemaContractError(
            "schema contract 위반 (dataset_context [SCHEMA DATA TYPES] 준수):\n"
            + "\n".join(f"- {x}" for x in issues[:12])
        )
