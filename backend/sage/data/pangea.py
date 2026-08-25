import anyio
import pandas as pd
import numpy as np
import json
import asyncio
import importlib.util
import concurrent.futures
from pathlib import Path
from typing import Any, List, Optional, Union, Dict, Tuple, Type
from datetime import datetime
import nest_asyncio
from filelock import FileLock, Timeout
from tqdm.asyncio import tqdm
import sys
import os
import hashlib
import shutil
import traceback

from sage.mcp import call
from sage.logg import error, info, warning

import cfg
from sage.data.dump_store import (
    cleanup_old_dumps,
    list_dump_files_for_model,
    load_dump_payload,
    plan_updates_from_dumps,
    resolve_field_tool,
    write_dump,
)
from sage.data.schema_types import (
    annotation_to_schema_type,
    cast_series_to_schema_type,
    coerce_value_for_schema,
    parse_schema_field_types,
)
from sage.data.schema_contract import validate_records_against_schema
from utils.conv import sanitize_tree
from utils.mod import load_module


def _as_flat_df(df: pd.DataFrame, keys: list[str] | None = None) -> pd.DataFrame:
    """keys(ticker, date 등)를 항상 컬럼으로 — _dfs·to_pandas·parquet 저장 공통."""
    if df is None or df.empty:
        return df.copy() if df is not None else df
    out = df.copy()
    if not isinstance(out.index, pd.RangeIndex):
        out = out.reset_index()
    if keys:
        for k in keys:
            if k not in out.columns and k in (out.index.names or []):
                out = out.reset_index()
                break
    return out.reset_index(drop=True)


def _upsert_flat(
        df: pd.DataFrame,
        df_update: pd.DataFrame,
        keys: list[str],
) -> pd.DataFrame:
    """
    flat df upsert — set_index 는 merge 순간만, 반환은 항상 flat (keys=컬럼).
    """
    if df_update.empty:
        return _as_flat_df(df, keys)
    df = _as_flat_df(df, keys)
    df_update = _as_flat_df(df_update, keys)
    if not keys:
        cols = df.columns.union(df_update.columns)
        merged = df.reindex(columns=cols).combine_first(df_update.reindex(columns=cols))
        return merged.reset_index(drop=True)

    missing = [k for k in keys if k not in df.columns]
    if missing:
        raise KeyError(f"existing dataframe missing key columns {missing}")
    missing_upd = [k for k in keys if k not in df_update.columns]
    if missing_upd:
        raise KeyError(f"update payload missing key columns {missing_upd}")

    left = df.set_index(keys)
    right = df_update.set_index(keys)
    cols = left.columns.union(right.columns)
    merged = right.reindex(columns=cols).combine_first(left.reindex(columns=cols))
    return merged.reset_index()


# 하위 호환 alias
_upsert_indexed = _upsert_flat

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

nest_asyncio.apply()


def _sanitize_json_tree(obj: Any) -> Any:
    """queue_update payload — date/datetime/numpy 등 JSON 직렬화 가능 값으로 변환."""
    return sanitize_tree(obj)


def _load_dump_records(path: Path) -> list[dict[str, Any]] | None:
    """dump JSON 1건 로드. 손상·형식 오류 시 삭제 후 None."""
    loaded = load_dump_payload(path)
    if loaded is None:
        return None
    records, _meta = loaded
    if not records:
        path.unlink(missing_ok=True)
        return None
    return records


def _coerce_date_value(val: Any) -> Any:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()[:10]
    return str(val)[:10]


def _load_model_schema_class(data_path: Path, model: str) -> Type | None:
    schema_path = data_path / "schema.py"
    if not schema_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"{data_path.name}.schema", schema_path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, model, None)


def map_payload_row(
    row: dict[str, Any],
    fields: list[str],
    keys: list[str],
    *,
    field_aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """pending/API raw dict → metadata fields. aliases = metadata.payload_field_aliases."""
    aliases = field_aliases or {}
    field_set = set(fields)
    mapped: dict[str, Any] = {}
    for raw_key, val in row.items():
        if val is None:
            continue
        canon = aliases.get(raw_key, raw_key)
        if canon in field_set:
            mapped[canon] = val
        elif raw_key in field_set:
            mapped[raw_key] = val
    for k in keys:
        if k not in mapped:
            continue
        if k == "date" or k.endswith("_date") or k.endswith("_dt"):
            mapped[k] = _coerce_date_value(mapped[k])
        elif isinstance(mapped[k], str):
            mapped[k] = mapped[k].strip()
    return {f: mapped[f] for f in fields if f in mapped}


def _coerce_row_to_schema(
    row: dict[str, Any],
    schema_types: dict[str, str],
) -> dict[str, Any]:
    if not schema_types:
        return row
    out = dict(row)
    for field, stype in schema_types.items():
        if field in out:
            out[field] = coerce_value_for_schema(out[field], stype)
    return out


class PangeaIO:
    def __init__(self, did: str, ver: str, primary_key_name: str):
        self.did = did
        self.ver = ver
        self.pk_name = primary_key_name
        self.pid = os.getpid()

        self.base_path = cfg.root_path / Path(f"data/{self.did}/pangea/{self.ver}")

        if not self.base_path.exists():
            raise ValueError(f"Invalid did: {self.did}")

        self.journals_dir = self.base_path / "journals"
        self.lock_dir = self.base_path / "lock"

        self.my_journal_path = self.journals_dir / f"patch_PID_{self.pid}.jsonl"

        self.journals_dir.mkdir(parents=True, exist_ok=True)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def write_journal_bulk(self, records: List[Dict[str, Any]]):
        if not records:
            return
        ts_str = pd.Timestamp.now().isoformat()
        lines = []
        for r in records:
            raw_val = r["val"]
            if hasattr(raw_val, "item") and not isinstance(raw_val, (pd.Timestamp, datetime)):
                raw_val = raw_val.item()
            elif isinstance(raw_val, (float, np.floating)) and np.isnan(raw_val):
                raw_val = None

            log_entry = {
                "pk_val": str(r["pk_val"]).strip(),
                "col": str(r["col"]).strip(),
                "val": raw_val,
                "ts": ts_str
            }
            lines.append(json.dumps(log_entry, ensure_ascii=False) + "\n")

        with open(self.my_journal_path, "a", encoding="utf-8") as f:
            f.writelines(lines)

    def load_master_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        data_path = self.base_path / "data.parquet"
        ts_path = self.base_path / "timestamps.parquet"

        # 1. 데이터 로드
        df = pd.read_parquet(data_path) if data_path.exists() else pd.DataFrame()
        ts_df = pd.read_parquet(ts_path) if ts_path.exists() else pd.DataFrame(index=df[self.pk_name])

        # 2. 인덱스 설정
        if not df.empty and df.index.name != self.pk_name:
            if self.pk_name in df.columns:
                df.set_index(self.pk_name, inplace=True)

        if not ts_df.empty and ts_df.index.name != self.pk_name:
            if self.pk_name in ts_df.columns:
                ts_df[self.pk_name] = df.index
                ts_df.set_index(self.pk_name, inplace=True)

        return df, ts_df

    def save_master_data(self, df: pd.DataFrame, ts_df: pd.DataFrame):
        """[최종] 인덱스를 컬럼으로 내려 저장하여 무결성 완벽 보존"""
        # 1. 저장 전 인덱스를 컬럼으로 변환 (인덱스 유실 방지)
        df_to_save = df.reset_index()
        ts_to_save = ts_df.reset_index()
        ts_to_save[self.pk_name] = datetime.now()

        # 2. 파켓으로 저장 (index=False: 이미 컬럼에 pk_name이 포함됨)
        df_to_save.to_parquet(self.base_path / "data.parquet", index=False)
        ts_to_save.to_parquet(self.base_path / "timestamps.parquet", index=False)

    def consolidate_all_journals_to_master(self, current_mem_df: pd.DataFrame, current_ts_df: pd.DataFrame) -> Tuple[
        pd.DataFrame, pd.DataFrame]:
        flock = FileLock(str(self.lock_dir / "main_data.lock"))
        flock.acquire(timeout=60)

        master_df = current_mem_df.copy()
        master_ts = current_ts_df.copy()

        try:
            for j_file in self.journals_dir.glob("patch_PID_*.jsonl"):
                if j_file.stat().st_size == 0: continue

                raw_data = pd.read_json(j_file, lines=True)
                patch_df = raw_data.pivot_table(index='pk_val', columns='col', values='val', aggfunc='last')
                patch_ts = raw_data.pivot_table(index='pk_val', columns='col', values='ts', aggfunc='last').apply(
                    pd.to_datetime)

                # [핵심] patch_df의 타입을 disk_df(마스터 데이터)의 타입에 맞게 캐스팅
                common_cols = [c for c in patch_df.columns if c in master_df.columns]
                if common_cols:
                    target_dtypes = {col: master_df[col].dtype for col in common_cols}
                    patch_df[common_cols] = patch_df[common_cols].astype(target_dtypes, errors='ignore')

                master_df.update(patch_df)
                master_ts.update(patch_ts)

                j_file.unlink()

            # 3. [개선] 퍼블릭 메서드 호출
            self.save_master_data(master_df, master_ts)

            return master_df, master_ts
        finally:
            flock.release()


def apply_schema(df: pd.DataFrame, schema: Any) -> pd.DataFrame:
    if df.empty or schema is None:
        return df

    fields = schema.model_fields
    pk = next(
        (name for name, f in fields.items() if (f.json_schema_extra or {}).get("primary_key") is True),
        list(fields.keys())[0],
    )
    current_schema_cols = [c for c in fields.keys() if c in df.columns]

    df = df[current_schema_cols].copy()

    for name in current_schema_cols:
        schema_type = annotation_to_schema_type(fields[name].annotation)
        if schema_type:
            df[name] = cast_series_to_schema_type(df[name], schema_type)

    return df

class PangeaMetadata:
    """메타데이터 로드 및 타겟 스키마/어댑터 관리를 전용으로 수행하는 클래스 (Decoupling 목적)"""

    def __init__(self, metadata_path: str = "metadata.json"):
        self.metadata_path = metadata_path
        self.sources: List[Dict[str, Any]] = []
        self.targets: List[Dict[str, Any]] = []
        self.tools: Dict[str, Any] = {}
        self.field_ttl: Dict[str, Any] = {}
        self.payload_field_aliases: Dict[str, str] = {}
        self._load_configs()

    def _load_configs(self):
        """메타데이터 파일을 읽어 내부 구조를 빌드"""
        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.sources = config.get("sources", [])
            self.targets = config.get("targets", [])
            self.tools = config.get("tools") or {}
            raw_fields = config.get("fields")
            self.field_ttl = raw_fields if isinstance(raw_fields, dict) else {}
            raw_aliases = config.get("payload_field_aliases")
            self.payload_field_aliases = (
                raw_aliases if isinstance(raw_aliases, dict) else {}
            )
        except Exception as e:
            print(f"[ERROR] 메타데이터 로드 실패: {str(e)}")
            raise e

    def __str__(self) -> str:
        """print() 호출 시 가독성을 높인 포맷 출력"""
        source_summary = ", ".join([f"{s.get('id')}({s.get('adapter')})" for s in self.sources])
        target_summary = ", ".join([t.get("model") for t in self.targets])

        return (
            f"<PangeaMetadata Configuration>\n"
            f" - Path: {self.metadata_path}\n"
            f" - Sources: [{source_summary}]\n"
            f" - Target Schemas: [{target_summary}]"
        )

    # def get_adapter_classes(self) -> Dict[str, Type]:
    #     """metadata의 source들에 지정된 어댑터 클래스들을 동적으로 추출하여 반환"""
    #     adapters = {}
    #     for source in self.sources:
    #         adapter_name = source.get("adapter")
    #         if adapter_name and hasattr(adapter_module, adapter_name):
    #             adapters[adapter_name] = getattr(adapter_module, adapter_name)
    #     return adapters

    # def get_target_fields(self, model_name: str) -> List[str]:
    #     """지정한 타겟 모델 스키마의 필드 목록을 반환"""
    #     for target in self.targets:
    #         if target.get("model") == model_name:
    #             return target.get("fields", [])
    #     return []


class PangeaExDataFrame:
    """멀티 스키마 처리 목적 PangeaExDataFrame 클래스"""

    def __init__(self, did, version='v1'):
        self.did = did
        self.version = version
        self.data_path = cfg.root_path / Path(f"data/{self.did}/pangea/{self.version}")
        self.adapters = {}
        self._dfs: Dict[str, pd.DataFrame] = {}

        self._load_config()
        self._load_adapter()
        self._load_parquet_data()

    def _load_config(self):
        metadata_path = self.data_path / "metadata.json"
        self.metadata = PangeaMetadata(metadata_path)
        # codegen·런타임 공용 — metadata.targets 와 동일 참조
        self.targets: list[dict[str, Any]] = self.metadata.targets
        self.models: list[str] = [
            t["model"] for t in self.targets if t.get("model")
        ]

    def _load_adapter(self):
        """metadata의 sources 정보를 바탕으로 어댑터 모듈을 동적 로드하고 인스턴스를 self.adapters에 저장"""
        # 어댑터 클래스들이 정의된 파일 경로 (기본적으로 data_path 내부의 adapter.py로 지정)
        adapter_file_path = self.data_path / "adapter.py"

        if not adapter_file_path.exists():
            # 만약 data_path 내부에 없다면 현재 작업 디렉토리(CWD)나 상위 경로에서 탐색 시도
            adapter_file_path = Path("adapter.py")
            if not adapter_file_path.exists():
                print(f"[ERROR] 어댑터 파일을 찾을 수 없습니다: {adapter_file_path.absolute()}")
                return

        # 제공된 동적 모듈 로더 함수를 활용하여 adapter 모듈 로드
        try:
            module_name = f"dynamic_adapter_{self.did}_{self.version}"
            adapter_module = load_module(module_name, str(adapter_file_path))
        except Exception as e:
            print(f"[ERROR] 어댑터 모듈 로드 실패: {str(e)}")
            raise e

        # metadata.sources를 순회하며 지정된 어댑터 클래스를 찾아 인스턴스화
        for source in self.metadata.sources:
            adapter_class_name = source.get("adapter")
            if not adapter_class_name:
                continue

            # 이미 로드된 어댑터인 경우 중복 생성 방지
            if adapter_class_name in self.adapters:
                continue

            # 로드된 모듈 내부에서 문자열 이름으로 클래스 객체 추출
            if hasattr(adapter_module, adapter_class_name):
                adapter_class = getattr(adapter_module, adapter_class_name)
                # 클래스 객체
                self.adapters[adapter_class_name] = adapter_class
            else:
                print(f"[WARNING] {adapter_file_path.name} 파일 내에 '{adapter_class_name}' 클래스가 존재하지 않습니다.")

    def get_target(self, model: str) -> dict[str, Any]:
        for target in self.metadata.targets:
            if target.get("model") == model:
                return target
        raise KeyError(
            f"metadata 에 model {model!r} 없음 — 사용 가능: {self.models}"
        )

    def _load_parquet_data(self):
        """metadata targets parquet → _dfs (항상 flat, keys=컬럼)."""
        for target in self.metadata.targets:
            model_name = target.get("model")
            file_name = target.get("path")
            keys = list(target.get("keys") or [])
            fields = target.get("fields", [])
            file_path = self.data_path / file_name

            if file_path.exists():
                df = _as_flat_df(pd.read_parquet(file_path), keys)
                if fields:
                    existing_fields = [col for col in fields if col in df.columns]
                    for k in keys:
                        if k in df.columns and k not in existing_fields:
                            existing_fields.insert(0, k)
                    df = df[existing_fields]
                if keys:
                    missing = [k for k in keys if k not in df.columns]
                    if missing:
                        raise KeyError(
                            f"{file_path.name}: metadata keys {missing} 없음 — "
                            f"columns={list(df.columns)}"
                        )
                self._dfs[model_name] = df.reset_index(drop=True)
            else:
                cols = list(dict.fromkeys(list(keys) + list(fields)))
                self._dfs[model_name] = (
                    pd.DataFrame(columns=cols) if cols else pd.DataFrame()
                )

    def to_pandas(self, model: str) -> pd.DataFrame:
        """flat DataFrame — keys 는 컬럼 (_dfs 와 동일)."""
        if model not in self._dfs:
            raise KeyError(
                f"'{model}'에 해당하는 데이터프레임을 찾을 수 없습니다. "
                f"현재 사용 가능한 키: {list(self._dfs.keys())}"
            )
        return self._dfs[model].copy()

    def plan_updates(self, model: str, keys=None, fields=None) -> List[Dict[str, Any]]:
        """
        metadata.json 루트 tools·fields + dump 폴더 TTL 로 만료·누락 필드 갱신 계획 생성.

        Args:
            model: metadata.targets[].model (dataset_context 에서 확인)
            keys: 검증 대상 행 식별 키 (기본: parquet 행). 호출측이 선정 목록을 넘기는 것이 원칙.
            fields: 검증 대상 컬럼 (기본: target fields)

        Returns:
            갱신 계획 목록. 각 항목:
            {"keys": list, "fields": list[str]}
            빈 list → MCP call 생략(최신). keys 생략 + 0행 parquet 은 빈 plan 이 되므로
            data 태스크는 반드시 keys=선정목록 을 넘긴다.
        """
        target_config = self.get_target(model)

        df = self._dfs[model]
        meta_keys = list(target_config.get("keys") or [])

        if keys is None:
            if not df.empty and meta_keys and all(k in df.columns for k in meta_keys):
                if len(meta_keys) > 1:
                    keys = list(df[meta_keys].itertuples(index=False, name=None))
                else:
                    keys = df[meta_keys[0]].tolist()
            else:
                keys = []

        if fields is None:
            key_set = set(meta_keys)
            cfg_fields = target_config.get("fields") or []
            fields = [f for f in cfg_fields if f in df.columns and f not in key_set]
            if not fields:
                fields = [c for c in df.columns if c not in key_set]

        cleanup_old_dumps(self.data_path, known_models=self.models)
        return plan_updates_from_dumps(
            self.data_path,
            model=model,
            target=target_config,
            metadata_tools=self.metadata.tools,
            metadata_field_ttl=self.metadata.field_ttl,
            sources=self.metadata.sources,
            req_keys=keys,
            req_fields=fields,
            known_models=self.models,
        )

    def queue_update(
        self,
        model: str,
        payload: List[Dict[str, Any]],
        tool_path: str | None = None,
    ):
        """
        report 갱신용 — 매핑 레코드를 dump 폴더에 저장 (apply_pending_updates 용).
        파일명: {model}-{tool-slug}-{timestamp}.json
        """
        if not payload:
            raise ValueError("queue_update: payload 가 비어 있습니다.")

        target_config = self.get_target(model)
        if not tool_path:
            sample_fields = [k for k in payload[0] if k not in (target_config.get("keys") or [])]
            for field in sample_fields:
                tool_path = resolve_field_tool(
                    self.metadata.tools, field, self.metadata.sources,
                )
                if tool_path:
                    break
        if not tool_path:
            raise ValueError(
                f"queue_update: tool_path 필수 — metadata.json 루트 tools 또는 sources[] 에 "
                f"tool_path 를 정의하세요 (model={model!r})"
            )

        schema_types = parse_schema_field_types(self.data_path / "schema.py").get(model, {})
        validate_records_against_schema(payload, schema_types, model=model)

        safe_payload = [_sanitize_json_tree(row) for row in payload]
        return write_dump(
            self.data_path,
            model=model,
            tool_path=tool_path,
            records=safe_payload,
        )

    def apply_pending_updates(self, model: str):
        """dump JSON → parquet upsert (신규 key 추가 + 동일 key 필드 갱신). dump 파일은 TTL 참고용으로 유지."""
        lock_path = self.data_path / f"{model}.lock"
        dump_files = list_dump_files_for_model(self.data_path, model)
        if not dump_files:
            return

        target_config = next(t for t in self.metadata.targets if t["model"] == model)
        keys = list(target_config.get("keys") or [])
        fields = list(target_config.get("fields") or [])
        target_path = self.data_path / target_config["path"]
        schema_types = parse_schema_field_types(self.data_path / "schema.py").get(model, {})

        lock = FileLock(str(lock_path))
        try:
            with lock.acquire(timeout=30):
                if model in self._dfs:
                    df = self._dfs[model].copy()
                else:
                    cols = list(dict.fromkeys(list(keys) + list(fields)))
                    df = pd.DataFrame(columns=cols) if cols else pd.DataFrame()
                applied = 0

                for p_file in dump_files:
                    payload = _load_dump_records(p_file)
                    if payload is None:
                        continue

                    normalized = [
                        _coerce_row_to_schema(
                            map_payload_row(
                                row,
                                fields,
                                keys,
                                field_aliases=self.metadata.payload_field_aliases,
                            ),
                            schema_types,
                        )
                        for row in payload
                        if isinstance(row, dict)
                    ]
                    normalized = [r for r in normalized if r and all(k in r for k in keys)]
                    if not normalized:
                        continue

                    df_update = pd.DataFrame(normalized)
                    df = _upsert_flat(df, df_update, keys)
                    applied += len(normalized)

                if applied == 0:
                    return

                df = _as_flat_df(df, keys)
                schema_cls = _load_model_schema_class(self.data_path, model)
                if schema_cls is not None:
                    df = apply_schema(df, schema_cls)
                temp_parquet = target_path.with_suffix(".parquet.tmp")
                df.to_parquet(temp_parquet, index=False)
                os.replace(temp_parquet, target_path)

                self._dfs[model] = df

                info(
                    f"[PangeaExDataFrame] {model} upsert done - "
                    f"rows={len(df)} applied_records={applied} path={target_path.name} "
                    f"(dump files retained for TTL)"
                )

        except Timeout as exc:
            raise RuntimeError(
                f"{model} apply_pending_updates: lock timeout ({lock_path}) — "
                "다른 프로세스가 갱신 중일 수 있습니다."
            ) from exc
        except Exception as exc:
            error(f"{model} apply_pending_updates 실패: {traceback.format_exc()}")
            raise


if __name__ == "__main__":
    pgdf = PangeaExDataFrame(did='did-stock-data-624ec9e9')
    for m in pgdf.models:
        print(m, pgdf.plan_updates(m))
