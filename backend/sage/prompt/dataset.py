import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import cfg
from sage.db import saged
from sage.errs import DataNotFoundError

from sage.data.schema_types import (
    pandas_dtype_to_schema_type,
    parse_schema_field_types,
    schema_types_prompt_block,
    validate_schema_models,
)
from utils.conv import json_dumps


async def read_schema_file(file_path: str) -> str:
    """schema.py 파일의 내용을 읽어 반환합니다."""
    if not os.path.exists(file_path):
        return "물리적 스키마 정의 파일(schema.py)이 존재하지 않습니다."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"스키마 파일 읽기 오류: {str(e)}"


async def get_data_profile(
    file_path: str,
    *,
    schema_types: dict[str, str] | None = None,
) -> str:
    """
    Parquet 파일의 핵심 통계만 추출하여 토큰 소모를 최소화하고
    LLM의 스키마 이해도를 극대화함.
    """
    if not os.path.exists(file_path):
        return "Data file not found."

    try:
        df = pd.read_parquet(file_path)
        total_len = len(df)

        col_info = {}
        schema_types = schema_types or {}
        for col in df.columns:
            series = df[col]
            schema_type = schema_types.get(col)

            if pd.api.types.is_string_dtype(series.dtype):
                working_series = series.astype(str)
            else:
                working_series = series

            col_schema_type = pandas_dtype_to_schema_type(series.dtype, schema_type=schema_type)
            stats = {
                "type": col_schema_type,
                "null_pct": f"{round((series.isnull().sum() / total_len) * 100, 1)}%",
                "unique": working_series.nunique(),
            }

            if pd.api.types.is_numeric_dtype(series.dtype):
                stats.update({
                    "min": round(float(series.min()), 2),
                    "max": round(float(series.max()), 2),
                    "avg": round(float(series.mean()), 2),
                })
            elif col_schema_type == "str":
                top_values = working_series.value_counts().head(3).index.tolist()
                stats["top_examples"] = top_values

            col_info[col] = stats

        profile = {
            "total_rows": total_len,
            "columns": list(df.columns),
            "schema_analysis": col_info,
            "samples": df.head(3).replace({np.nan: None}).to_dict(orient="records"),
        }

        return json_dumps(profile)

    except Exception as e:
        return f"Error profiling parquet: {str(e)}"


def _has_parquet_files(target_dir: Path) -> bool:
    if not target_dir.exists():
        return False
    return any(target_dir.glob("*.parquet"))


async def _profile_pangea_tables(
    target_dir: Path,
    model_fields: dict[str, dict[str, str]],
) -> str:
    schema_path = target_dir / "schema.py"
    if not model_fields:
        model_fields = parse_schema_field_types(schema_path)
    metadata_path = target_dir / "metadata.json"
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        tables: dict = {}
        for target in metadata.get("targets", []):
            rel_path = target.get("path")
            if not rel_path:
                continue
            parquet_path = target_dir / rel_path
            if not parquet_path.is_file():
                continue
            schema_types = model_fields.get(target.get("model") or "", {})
            profile_raw = await get_data_profile(
                str(parquet_path),
                schema_types=schema_types or None,
            )
            try:
                tables[rel_path] = json.loads(profile_raw)
            except json.JSONDecodeError:
                tables[rel_path] = profile_raw

        if tables:
            return json_dumps({"tables": tables})

    legacy_path = target_dir / "data.parquet"
    if legacy_path.is_file():
        return await get_data_profile(str(legacy_path))

    return "Data file not found."


async def load_schema(did: str) -> str:
    """
    metadata.json 기준 다중 parquet 프로파일 + PangeaDataFrame 경로.
    """
    doc = await saged.db["data"].find_one({"_id": did})
    if not doc:
        raise DataNotFoundError(did)

    version = doc.get("version", "v1")
    target_dir = Path(cfg.root_path) / "data" / did / "pangea" / version
    schema_path = target_dir / "schema.py"

    schema_spec = await read_schema_file(str(schema_path))
    model_fields = parse_schema_field_types(schema_path)
    try:
        validate_schema_models(model_fields)
    except ValueError:
        pass
    data_profile = await _profile_pangea_tables(target_dir, model_fields)
    metadata_path = target_dir / "metadata.json"
    targets_json = "[]"
    tools_json = "{}"
    field_ttl_json = "{}"
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        targets_json = json_dumps(metadata.get("targets") or [], pretty=True)
        tools_json = json_dumps(metadata.get("tools") or {}, pretty=True)
        raw_fields = metadata.get("fields")
        field_ttl_json = json_dumps(raw_fields if isinstance(raw_fields, dict) else {}, pretty=True)

    return (
        f"### [DATASET CONTEXT]\n"
        f"- ID: {did}\n"
        f"- Name: {doc.get('name', 'N/A')}\n"
        f"- Description: {doc.get('description', 'N/A')}\n"
        f"- Edition: p2\n\n"
        f"### [PANGEA TARGETS — codegen 시 model 인자는 여기 이름만 사용]\n"
        f"`metadata.json` 의 `targets[]`. **모델명 추측·하드코딩 금지** (예: PangeaSchema).\n\n"
        f"```json\n{targets_json}\n```\n\n"
        f"- `model`: `to_pandas(model)`, `plan_updates(model)`, `queue_update(model, ...)`\n"
        f"- `keys`: parquet index / upsert 키\n"
        f"- `fields`: 허용 컬럼 (list)\n"
        f"- `path`: parquet 파일명\n\n"
        f"### [PANGEA TOOLS — metadata.json 루트]\n"
        f"tool_path → 제공 fields (dump TTL·queue_update 용)\n\n"
        f"```json\n{tools_json}\n```\n\n"
        f"### [PANGEA FIELD TTL — metadata.json 루트 `fields`]\n"
        f"```json\n{field_ttl_json}\n```\n\n"
        f"{schema_types_prompt_block()}\n"
        f"### [UNIFIED SCHEMA DEFINITION]\n"
        f"```python\n{schema_spec}\n```\n\n"
        f"### [DATA PROFILE & STATISTICS]\n"
        f"{data_profile}"
    )


__all__ = [
    "get_data_profile",
    "load_schema",
    "parse_schema_field_types",
    "read_schema_file",
    "pandas_dtype_to_schema_type",
]
