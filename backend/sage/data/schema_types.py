"""통합 스키마(schema.py) 데이터 타입 — 단일 정의·변환·검증."""

from __future__ import annotations

import ast
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# schema.py BaseModel 필드 annotation 에만 허용
SCHEMA_TYPES: frozenset[str] = frozenset({"str", "int", "float", "bool", "date", "datetime"})

# API·레거시 alias → canonical
TYPE_ALIASES: dict[str, str] = {
    "string": "str",
    "text": "str",
    "integer": "int",
    "long": "int",
    "int64": "int",
    "int32": "int",
    "number": "float",
    "double": "float",
    "float64": "float",
    "float32": "float",
    "boolean": "bool",
}

PANDAS_DTYPE_TO_SCHEMA: dict[str, str] = {
    "float64": "float",
    "float32": "float",
    "Float64": "float",
    "float16": "float",
    "int64": "int",
    "int32": "int",
    "Int64": "int",
    "Int32": "int",
    "uint64": "int",
    "uint32": "int",
    "bool": "bool",
    "boolean": "bool",
    "object": "str",
    "string": "str",
    "category": "str",
    "datetime64[ns]": "datetime",
    "datetime64[us]": "datetime",
    "datetime64[ms]": "datetime",
    "datetime64[s]": "datetime",
    "date": "date",
}

# canonical → pandas astype (parquet 저장·로드)
SCHEMA_TO_PANDAS: dict[str, str] = {
    "str": "string",
    "int": "Int64",
    "float": "float64",
    "bool": "boolean",
    "date": "object",
    "datetime": "datetime64[ns]",
}

def normalize_schema_type(type_name: str) -> str:
    """alias·대소문자 정규화. 허용 집합 밖이면 ValueError."""
    key = (type_name or "").strip().lower()
    key = TYPE_ALIASES.get(key, key)
    if key not in SCHEMA_TYPES:
        allowed = ", ".join(sorted(SCHEMA_TYPES))
        raise ValueError(f"unsupported schema type {type_name!r} — allowed: {allowed}")
    return key

def pandas_dtype_to_schema_type(dtype: Any, *, schema_type: str | None = None) -> str:
    """parquet/pandas dtype → schema canonical (float64 → float)."""
    if schema_type:
        return normalize_schema_type(schema_type)
    dtype_str = str(dtype)
    if dtype_str in PANDAS_DTYPE_TO_SCHEMA:
        return PANDAS_DTYPE_TO_SCHEMA[dtype_str]
    if dtype_str.startswith("datetime64"):
        return "datetime"
    if dtype_str.startswith("string"):
        return "str"
    return dtype_str

def schema_type_to_pandas_dtype(schema_type: str) -> str:
    """canonical schema type → pandas storage dtype."""
    canonical = normalize_schema_type(schema_type)
    return SCHEMA_TO_PANDAS[canonical]

def _annotation_ast_to_schema_type(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Subscript):
        return _annotation_ast_to_schema_type(node.slice)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _annotation_ast_to_schema_type(node.left) or _annotation_ast_to_schema_type(
            node.right
        )
    return None

def parse_schema_field_types(schema_path: str | Path) -> dict[str, dict[str, str]]:
    """schema.py BaseModel → {ModelName: {field: canonical_type}}."""
    path = Path(schema_path)
    if not path.is_file():
        return {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    models: dict[str, dict[str, str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        fields: dict[str, str] = {}
        for item in node.body:
            if not isinstance(item, ast.AnnAssign) or not isinstance(item.target, ast.Name):
                continue
            raw = _annotation_ast_to_schema_type(item.annotation)
            if not raw:
                continue
            try:
                fields[item.target.id] = normalize_schema_type(raw)
            except ValueError:
                fields[item.target.id] = raw
        if fields:
            models[node.name] = fields
    return models

def validate_schema_models(models: dict[str, dict[str, str]]) -> None:
    """모든 필드 타입이 SCHEMA_TYPES 인지 검증."""
    for model, fields in models.items():
        for field, type_name in fields.items():
            try:
                normalize_schema_type(type_name)
            except ValueError as exc:
                raise ValueError(f"{model}.{field}: {exc}") from exc

def annotation_to_schema_type(annotation: Any) -> str | None:
    """Pydantic field annotation → canonical type."""
    if annotation is None:
        return None
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        args = getattr(annotation, "__args__", ())
        for arg in args:
            if arg is type(None):
                continue
            result = annotation_to_schema_type(arg)
            if result:
                return result
        return None
    if annotation is str:
        return "str"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is bool:
        return "bool"
    if annotation is date:
        return "date"
    if annotation is datetime:
        return "datetime"
    name = getattr(annotation, "__name__", str(annotation))
    try:
        return normalize_schema_type(name)
    except ValueError:
        return None

def coerce_value_for_schema(val: Any, schema_type: str) -> Any:
    """단일 값 → schema canonical (queue_update·upsert 직전)."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    canonical = normalize_schema_type(schema_type)

    if canonical == "int":
        if isinstance(val, (datetime, date)):
            return int(val.strftime("%Y%m%d"))
        if isinstance(val, pd.Timestamp):
            return int(val.strftime("%Y%m%d"))
        if hasattr(val, "strftime") and not isinstance(val, str):
            try:
                return int(val.strftime("%Y%m%d"))
            except Exception:
                pass
        if isinstance(val, (int, np.integer)) and not isinstance(val, bool):
            return int(val)
        if isinstance(val, (float, np.floating)) and not np.isnan(val):
            return int(val)
        s = str(val).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", s):
            return int(s[:10].replace("-", ""))
        if re.match(r"^\d{8}$", s):
            return int(s)
        digits = re.sub(r"[^\d]", "", s)
        return int(digits) if digits else val

    if canonical == "date":
        if isinstance(val, date) and not isinstance(val, datetime):
            return val.isoformat()
        if isinstance(val, (datetime, pd.Timestamp)) or hasattr(val, "isoformat"):
            try:
                return val.isoformat()[:10]  # type: ignore[union-attr]
            except Exception:
                pass
        s = str(val).strip()
        return s[:10] if len(s) >= 10 else s

    if canonical == "datetime":
        if isinstance(val, datetime):
            return val
        if isinstance(val, pd.Timestamp):
            return val.to_pydatetime()
        parsed = pd.to_datetime(val, errors="coerce")
        if pd.isna(parsed):
            return val
        return parsed.to_pydatetime()

    if canonical == "float":
        return float(val)

    if canonical == "bool":
        return bool(val)

    if canonical == "str":
        return str(val).strip()

    return val


def _coerce_object_series_to_int(series: pd.Series) -> pd.Series:
    return series.map(lambda v: coerce_value_for_schema(v, "int"))


def cast_series_to_schema_type(series: pd.Series, schema_type: str) -> pd.Series:
    """DataFrame 컬럼을 통합 스키마 타입에 맞게 변환."""
    canonical = normalize_schema_type(schema_type)
    out = series.copy()

    if canonical == "str":
        out = out.astype("string").str.strip()
        out = out.replace({"nan": None, "None": None, "": None})
        return out

    if canonical == "int":
        if out.dtype == object:
            out = _coerce_object_series_to_int(out)
        return pd.to_numeric(out, errors="coerce").astype("Int64")

    if canonical == "float":
        if out.dtype == object:
            out = out.astype(str).str.replace(r"[^\d.-]", "", regex=True)
        return pd.to_numeric(out, errors="coerce").astype("float64")

    if canonical == "bool":
        return out.astype("boolean")

    if canonical == "date":
        parsed = pd.to_datetime(out, errors="coerce")
        return parsed.dt.date

    if canonical == "datetime":
        return pd.to_datetime(out, errors="coerce")

    return out

def schema_types_prompt_block() -> str:
    """LLM·dataset_context 용 타입 규격 요약."""
    rows = "\n".join(
        f"| `{t}` | `{SCHEMA_TO_PANDAS[t]}` |"
        for t in sorted(SCHEMA_TYPES)
    )
    return (
        "### [SCHEMA DATA TYPES — schema.py 전용]\n"
        "통합 스키마 필드 annotation·프로파일 `type`·metadata 는 **아래 canonical 만** 사용.\n"
        "`string`/`float64`/`int64`/`number` 등 **별칭·pandas dtype 금지**.\n\n"
        "| canonical | pandas 저장 |\n"
        "|-----------|-------------|\n"
        f"{rows}\n"
    )
