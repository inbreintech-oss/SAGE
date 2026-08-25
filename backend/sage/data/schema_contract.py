"""schema.py 런타임 contract — data 레이어 (report 의존 없음)."""

from __future__ import annotations

import re
from typing import Any

from sage.data.schema_types import normalize_schema_type


class SchemaContractError(ValueError):
    """queue_update / record 가 schema.py 필드 타입과 불일치."""


def value_matches_schema_type(val: Any, schema_type: str) -> bool:
    """런타임 단일 값 — schema canonical 타입 일치 여부 (strict)."""
    if val is None:
        return True
    try:
        canonical = normalize_schema_type(schema_type)
    except ValueError:
        return True

    if canonical == "str":
        return isinstance(val, str)
    if canonical == "int":
        if isinstance(val, bool):
            return False
        return isinstance(val, int)
    if canonical == "float":
        return isinstance(val, (int, float)) and not isinstance(val, bool)
    if canonical == "bool":
        return isinstance(val, bool)
    if canonical == "date":
        if isinstance(val, str) and re.match(r"^\d{4}-\d{2}-\d{2}", val.strip()):
            return True
        from datetime import date

        return isinstance(val, date) and not hasattr(val, "hour")
    if canonical == "datetime":
        from datetime import datetime

        return isinstance(val, datetime) or hasattr(val, "to_pydatetime")
    return True


def validate_records_against_schema(
    records: list[dict[str, Any]],
    field_types: dict[str, str],
    *,
    model: str = "",
) -> None:
    """queue_update 직전 — 모든 record 필드 타입 검사."""
    if not records or not field_types:
        return
    errors: list[str] = []
    for i, row in enumerate(records):
        if not isinstance(row, dict):
            errors.append(f"record[{i}]: dict 가 아님")
            continue
        for field, expected in field_types.items():
            if field not in row:
                continue
            val = row[field]
            if val is None:
                continue
            if not value_matches_schema_type(val, expected):
                got = type(val).__name__
                errors.append(
                    f"record[{i}].{field}: schema `{expected}` ≠ 실제 `{got}` "
                    f"(값을 변환하지 말고 API·schema 타입에 맞게 매핑)"
                )
    if errors:
        prefix = f"{model} " if model else ""
        raise SchemaContractError(
            f"{prefix}schema contract 위반:\n" + "\n".join(f"- {e}" for e in errors[:15])
        )
