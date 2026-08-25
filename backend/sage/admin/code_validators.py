"""Common code field validation."""

from __future__ import annotations

import re

GROUP_NAME_RE = re.compile(r"^[\uAC00-\uD7A3a-zA-Z0-9()\[\]{}]+$")
CODE_RE = re.compile(r"^[a-zA-Z0-9]+$")


def validate_group_name(name: str) -> str | None:
    trimmed = name.strip()
    if not trimmed:
        return "그룹코드명은 필수입니다."
    if not GROUP_NAME_RE.match(trimmed):
        return "그룹코드명은 한글, 영문, 숫자, 괄호 ()[]{} 만 입력 가능합니다."
    return None


def validate_detail_name(name: str) -> str | None:
    trimmed = name.strip()
    if not trimmed:
        return "명칭은 필수입니다."
    if not GROUP_NAME_RE.match(trimmed):
        return "명칭은 한글, 영문, 숫자, 괄호 ()[]{} 만 입력 가능합니다."
    return None


def validate_code(code: str, *, label: str = "코드") -> str | None:
    trimmed = code.strip()
    if not trimmed:
        return f"{label}은(는) 필수입니다."
    if not CODE_RE.match(trimmed):
        return f"{label}는 영문, 숫자만 입력 가능합니다."
    return None
