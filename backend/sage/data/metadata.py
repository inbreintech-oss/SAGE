"""Pangea metadata.json 로드 및 target parquet 경로 해석."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

import cfg

DEFAULT_MODEL = "PangeaSchema"
LEGACY_PARQUET = "data.parquet"


class PangeaSource(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    adapter: str | None = None
    tool_path: str | None = None


class PangeaTarget(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    path: str
    keys: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list, description="parquet 컬럼명 list")


class PangeaMetadataDoc(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    sources: list[PangeaSource] = Field(default_factory=list)
    targets: list[PangeaTarget] = Field(default_factory=list)
    tools: dict[str, Any] = Field(
        default_factory=dict,
        description='루트 tool_path → {fields: [...]}',
    )
    field_ttl: dict[str, Any] = Field(
        default_factory=dict,
        alias="fields",
        description='루트 필드 TTL — {"_default_ttl": 1, "debt_rate": {"ttl": 10}}',
    )


def pangea_dir_for(did: str, version: str = "v1") -> Path:
    return Path(cfg.root_path) / "data" / did / "pangea" / version


def load_metadata_doc(pangea_dir: Path) -> PangeaMetadataDoc:
    metadata_path = pangea_dir / "metadata.json"
    if not metadata_path.is_file():
        return PangeaMetadataDoc()
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    return PangeaMetadataDoc.model_validate(raw)


class PangeaDataMetadata:
    """did/version 기준 metadata.json 핸들러."""

    def __init__(self, pangea_dir: Path, doc: PangeaMetadataDoc | None = None):
        self.pangea_dir = pangea_dir
        self.doc = doc if doc is not None else load_metadata_doc(pangea_dir)

    @classmethod
    def from_did(cls, did: str, version: str = "v1") -> PangeaDataMetadata:
        return cls(pangea_dir_for(did, version))

    @property
    def targets(self) -> list[PangeaTarget]:
        return self.doc.targets

    @property
    def models(self) -> list[str]:
        return [t.model for t in self.doc.targets if t.model]

    def has_targets(self) -> bool:
        return bool(self.doc.targets)

    def get_target(self, model: str) -> PangeaTarget:
        for target in self.doc.targets:
            if target.model == model:
                return target
        raise KeyError(
            f"metadata 에 model {model!r} 없음 — 사용 가능: {self.models}"
        )

    def resolve_target(self, model: str = DEFAULT_MODEL) -> PangeaTarget:
        if self.has_targets():
            return self.get_target(model)
        if model != DEFAULT_MODEL:
            raise KeyError(
                f"metadata.json 없음 — model {model!r} 조회 불가 (기본: {DEFAULT_MODEL!r})"
            )
        return PangeaTarget(model=DEFAULT_MODEL, path=LEGACY_PARQUET)

    def resolve_parquet_path(self, model: str = DEFAULT_MODEL) -> Path:
        target = self.resolve_target(model)
        return self.pangea_dir / target.path

    def target_info(self, model: str = DEFAULT_MODEL) -> dict[str, Any]:
        target = self.resolve_target(model)
        return {
            "model": target.model,
            "path": target.path,
            "keys": target.keys,
            "fields": target.fields,
        }

    def read_dataframe(self, model: str = DEFAULT_MODEL) -> pd.DataFrame:
        path = self.resolve_parquet_path(model)
        if not path.is_file():
            raise FileNotFoundError(str(path))

        df = pd.read_parquet(path)
        if not self.has_targets():
            return df

        target = self.get_target(model)
        if not target.fields:
            return df

        columns: list[str] = []
        for key in target.keys:
            if key in df.columns and key not in columns:
                columns.append(key)
        for field in target.fields:
            if field in df.columns and field not in columns:
                columns.append(field)
        if columns:
            return df[columns]
        return df

    def sample_records(
        self,
        model: str = DEFAULT_MODEL,
        limit: int = 10,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        df = self.read_dataframe(model)
        sampled = (
            df.head(limit)
            .replace({pd.NA: None, float("nan"): None, float("inf"): None, float("-inf"): None})
            .to_dict(orient="records")
        )
        return sampled or [], self.target_info(model)


__all__ = [
    "DEFAULT_MODEL",
    "LEGACY_PARQUET",
    "PangeaDataMetadata",
    "PangeaMetadataDoc",
    "PangeaSource",
    "PangeaTarget",
    "load_metadata_doc",
    "pangea_dir_for",
]
