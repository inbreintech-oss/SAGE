"""Pangea dump 폴더 — TTL·파일명·retention (기존 .ts / pending 대체)."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

import cfg
from sage.logg import info, warning
from utils.conv import json_dumps, sanitize_tree

DUMP_DIR_NAME = "dump"
LEGACY_PENDING_DIR = "pending"
DEFAULT_TTL_DAYS = 1
DEFAULT_RETENTION_DAYS = 30


def slug_path(path: str) -> str:
    """도구 path → 파일명 slug (소문자, `/`·`_` → `-`)."""
    return path.strip().lower().replace("/", "-").replace("_", "-")


def dump_dir(data_path: Path) -> Path:
    return data_path / DUMP_DIR_NAME


def pangea_data_path(did: str, version: str = "v1") -> Path:
    """데이터셋 pangea 루트 — unify·report 공통."""
    return cfg.root_path / "data" / did / "pangea" / version


def key_slug(key: Any) -> str:
    """행 식별자 → dump 하위 디렉터리명."""
    norm = _normalize_key(key)
    if isinstance(norm, tuple):
        return "__".join(_key_part_slug(part) for part in norm)
    return _key_part_slug(norm)


def _key_part_slug(part: Any) -> str:
    s = str(part).strip()
    return re.sub(r'[<>:"/\\|?*\s]', "_", s)


def dump_tool_response_path(
    data_path: Path,
    model: str,
    tool_path: str,
    key: Any,
) -> Path:
    """`dump/{model}/{tool_slug}/{key_slug}/response.json`"""
    return (
        dump_dir(data_path)
        / model
        / slug_path(tool_path)
        / key_slug(key)
        / "response.json"
    )


def _fields_for_tool(metadata_tools: dict[str, Any] | None, tool_path: str) -> set[str]:
    tools = metadata_tools if isinstance(metadata_tools, dict) else {}
    cfg_entry = tools.get(tool_path)
    if isinstance(cfg_entry, dict):
        return {str(f) for f in (cfg_entry.get("fields") or [])}
    return set()


def dump_tool_response(
    did: str,
    model: str,
    tool_path: str,
    key: Any,
    response: Any,
    *,
    version: str = "v1",
) -> Path:
    """
    MCP 원본 응답 저장 — key·tool 단위 TTL 기준선.
    경로: dump/{model}/{tool_slug}/{key_slug}/response.json
    """
    data_path = pangea_data_path(did, version)
    ts = int(time.time() * 1000)
    file_path = dump_tool_response_path(data_path, model, tool_path, key)
    payload = {
        "tool_path": tool_path,
        "model": model,
        "key": _normalize_key(key),
        "created_at_ms": ts,
        "response": sanitize_tree(response),
    }
    _atomic_write_json(file_path, payload, pretty=True)
    return file_path


def dump_filename(model: str, tool_path: str, timestamp_ms: int | None = None) -> str:
    ts = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
    return f"{model}-{slug_path(tool_path)}-{ts}.json"


def parse_dump_filename(
    name: str,
    known_models: list[str],
) -> tuple[str, str, int] | None:
    """`{model}-{tool-slug}-{timestamp}.json` 파싱."""
    if not name.endswith(".json"):
        return None
    for model in sorted(known_models, key=len, reverse=True):
        prefix = f"{model}-"
        if not name.startswith(prefix):
            continue
        rest = name[len(prefix) : -5]
        sep = rest.rfind("-")
        if sep <= 0:
            continue
        ts_part = rest[sep + 1 :]
        if not ts_part.isdigit():
            continue
        return model, rest[:sep], int(ts_part)
    return None


def _normalize_key(key: Any) -> Any:
    if isinstance(key, (list, tuple)):
        return tuple(_normalize_key(k) for k in key)
    if isinstance(key, (date, datetime)):
        return key.isoformat()
    if hasattr(key, "item"):
        return key.item()
    return key


def _is_expired(timestamp_ms: int, ttl_days: int) -> bool:
    last_date = datetime.fromtimestamp(timestamp_ms / 1000).date()
    return (date.today() - last_date).days >= ttl_days


def _target_columns(target: dict[str, Any]) -> list[str]:
    """targets[].fields — 컬럼명 list (TTL dict 와 구분)."""
    raw = target.get("fields")
    return list(raw) if isinstance(raw, list) else []


def _ttl_policy(metadata_field_ttl: dict[str, Any] | None) -> dict[str, Any]:
    """metadata.json 루트 fields — 필드별 TTL 정책."""
    if isinstance(metadata_field_ttl, dict):
        return metadata_field_ttl
    return {}


def resolve_field_tool(
    metadata_tools: dict[str, Any] | None,
    field: str,
    sources: list[dict[str, Any]],
) -> str | None:
    """
    metadata.json 루트 tools 에서 필드 → tool_path.
    형식: {"kis/stock": {"fields": ["close_price", ...]}, ...}
    """
    tools = metadata_tools if isinstance(metadata_tools, dict) else {}

    for tool_path, cfg in tools.items():
        if str(tool_path).startswith("_"):
            continue
        path = str(tool_path).strip()
        if not path:
            continue
        if isinstance(cfg, dict):
            flds = cfg.get("fields") or []
            if field in flds:
                return path

    for src in sources:
        if src.get("type") == "tool":
            path = (src.get("tool_path") or "").strip()
            if path:
                return path
    return None


def resolve_field_ttl(metadata_field_ttl: dict[str, Any] | None, field: str) -> int:
    """
    metadata.json 루트 fields — {"_default_ttl": 1, "debt_rate": {"ttl": 10}, ...}
    """
    policy = _ttl_policy(metadata_field_ttl)
    val = policy.get(field)
    if isinstance(val, dict) and val.get("ttl") is not None:
        return int(val["ttl"])
    if isinstance(val, (int, float)):
        return int(val)

    for key in ("_default_ttl", "default_ttl"):
        if policy.get(key) is not None:
            return int(policy[key])

    return DEFAULT_TTL_DAYS


def list_tool_paths(metadata_tools: dict[str, Any] | None) -> list[str]:
    """metadata.json 루트 tools 에 등록된 tool_path 목록."""
    tools = metadata_tools if isinstance(metadata_tools, dict) else {}
    out: list[str] = []
    for tool_path, cfg in tools.items():
        if str(tool_path).startswith("_"):
            continue
        path = str(tool_path).strip()
        if not path:
            continue
        if isinstance(cfg, dict) and cfg.get("fields"):
            out.append(path)
    return out


def _atomic_write_json(path: Path, data: Any, *, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    text = json_dumps(data, pretty=pretty)
    json.loads(text)
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_dump(
    data_path: Path,
    *,
    model: str,
    tool_path: str,
    records: list[dict[str, Any]],
    timestamp_ms: int | None = None,
) -> Path:
    """dump JSON 저장 — wrapper 메타 + records."""
    ts = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
    out_dir = dump_dir(data_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / dump_filename(model, tool_path, ts)
    payload = {
        "tool_path": tool_path,
        "model": model,
        "created_at_ms": ts,
        "records": records,
    }
    _atomic_write_json(file_path, payload, pretty=True)
    return file_path


def _extract_records(payload: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """legacy list·wrapper dict·response dict → (records, meta)."""
    if payload is None:
        return [], {}
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)], {}
    if isinstance(payload, dict):
        records = payload.get("records")
        if isinstance(records, list):
            meta = {k: v for k, v in payload.items() if k != "records"}
            return [r for r in records if isinstance(r, dict)], meta
        if "response" in payload:
            meta = {k: v for k, v in payload.items() if k != "response"}
            meta["_kind"] = "response"
            resp = payload.get("response")
            if isinstance(resp, dict) and resp.get("status") is not None:
                meta["_status"] = resp.get("status")
            return [], meta
    return [], {}


def _list_model_dump_paths(data_path: Path, model: str) -> list[Path]:
    """model 관련 dump 파일 — legacy flat + 계층형 response/data."""
    paths: list[Path] = []
    out_dir = dump_dir(data_path)
    paths.extend(out_dir.glob(f"{model}-*.json"))
    model_dir = out_dir / model
    if model_dir.is_dir():
        paths.extend(model_dir.rglob("response.json"))
        paths.extend(model_dir.rglob("data.json"))
    legacy_pending = list((data_path / LEGACY_PENDING_DIR).glob(f"pending_updates_{model}_*.json"))
    paths.extend(legacy_pending)
    return sorted({p.resolve() for p in paths}, key=lambda p: p.stat().st_mtime)


def _resolve_dump_tool_path(
    path: Path,
    meta: dict[str, Any],
    known_models: list[str],
) -> str:
    tool_path = (meta.get("tool_path") or "").strip()
    if tool_path:
        return tool_path
    parsed = parse_dump_filename(path.name, known_models)
    if parsed:
        return parsed[1]
    if path.parent.name and path.parent.parent.name:
        # dump/{model}/{tool_slug}/{key}/file.json
        return path.parent.parent.name.replace("-", "/")
    return ""


def _keys_from_dump_meta(
    meta: dict[str, Any],
    records: list[dict[str, Any]],
    meta_keys: list[str],
) -> set[Any]:
    if meta.get("key") is not None:
        return {_normalize_key(meta["key"])}
    return _infer_keys_from_records(records, meta_keys)


def _keys_from_dump(
    path: Path,
    meta: dict[str, Any],
    records: list[dict[str, Any]],
    meta_keys: list[str],
) -> set[Any]:
    keys = _keys_from_dump_meta(meta, records, meta_keys)
    if keys:
        return keys
    if path.name in ("response.json", "data.json") and path.parent.name:
        return {_normalize_key(path.parent.name)}
    return keys


def _dump_response_succeeded(meta: dict[str, Any]) -> bool:
    """FAIL·예외 dump 는 TTL 커버리지로 치지 않는다 — 재조회 대상."""
    status = meta.get("_status")
    if status is None:
        return False
    return str(status).strip().upper() == "SUCCESS"


def list_dump_keys_for_model(
    data_path: Path,
    *,
    model: str,
    meta_keys: list[str],
    known_models: list[str] | None = None,
) -> list[Any]:
    """parquet 0행일 때 dump 폴더에서 재조회 키를 복원한다 (FAIL dump 포함)."""
    del known_models
    ordered: list[Any] = []
    seen: set[Any] = set()
    for path in _list_model_dump_paths(data_path, model):
        loaded = load_dump_payload(path)
        if loaded is None:
            continue
        records, meta = loaded
        for key in _keys_from_dump(path, meta, records, meta_keys):
            if key in seen:
                continue
            seen.add(key)
            ordered.append(key)
    return ordered


def load_dump_payload(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    """dump JSON 1건 로드. 손상 시 삭제 후 None."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:
        warning(f"[PangeaDump] JSON 손상 — 삭제: {path.name} ({exc})")
        path.unlink(missing_ok=True)
        return None
    except OSError as exc:
        warning(f"[PangeaDump] 읽기 실패 — 건너뜀: {path.name} ({exc})")
        return None

    records, meta = _extract_records(payload)
    if payload is not None and not isinstance(payload, (list, dict)):
        warning(
            f"[PangeaDump] 형식 오류 — 삭제: {path.name} "
            f"(expected list|dict, got {type(payload).__name__})"
        )
        path.unlink(missing_ok=True)
        return None
    return records, meta


def dump_timestamp_ms(path: Path, meta: dict[str, Any], known_models: list[str]) -> int:
    if meta.get("created_at_ms"):
        return int(meta["created_at_ms"])
    parsed = parse_dump_filename(path.name, known_models)
    if parsed:
        return parsed[2]
    legacy = re.match(r"^pending_updates_(.+)_(\d+)\.json$", path.name)
    if legacy and legacy.group(2).isdigit():
        return int(legacy.group(2))
    return int(path.stat().st_mtime * 1000)


def _infer_fields_from_records(
    records: list[dict[str, Any]],
    keys: list[str],
    fields: list[str],
) -> set[str]:
    field_set = set(fields)
    key_set = set(keys)
    found: set[str] = set()
    for row in records:
        for col in row:
            if col in field_set and col not in key_set:
                found.add(col)
    return found or field_set


def _infer_keys_from_records(
    records: list[dict[str, Any]],
    keys: list[str],
) -> set[Any]:
    if not keys or not records:
        return set()
    out: set[Any] = set()
    for row in records:
        if not all(k in row for k in keys):
            continue
        if len(keys) > 1:
            out.add(_normalize_key(tuple(row[k] for k in keys)))
        else:
            out.add(_normalize_key(row[keys[0]]))
    return out


def _first_key_part(key: Any) -> Any:
    if isinstance(key, (tuple, list)):
        return _normalize_key(key[0])
    return _normalize_key(key)


def _match_common_keys(
    meta_keys: list[str],
    ret_keys_norm: list[Any],
    dump_keys: set[Any],
) -> list[Any]:
    """req_keys 와 dump_keys 교집합 — 복합키 model 에 ticker-only req 도 허용."""
    is_multi = bool(meta_keys) and len(meta_keys) > 1
    req_scalar = bool(ret_keys_norm) and all(
        not isinstance(k, (tuple, list)) for k in ret_keys_norm
    )
    dump_scalar = bool(dump_keys) and all(
        not isinstance(k, (tuple, list)) for k in dump_keys
    )
    if is_multi and req_scalar:
        dump_tickers = {_first_key_part(k) for k in dump_keys}
        return [k for k in ret_keys_norm if k in dump_tickers]
    if is_multi and dump_scalar:
        dump_tickers = {_normalize_key(k) for k in dump_keys}
        return [k for k in ret_keys_norm if _first_key_part(k) in dump_tickers]
    if is_multi:
        return [k for k in ret_keys_norm if k in dump_keys]
    box_keys_slim = (
        {_first_key_part(k) for k in dump_keys}
        if any(isinstance(k, (tuple, list)) for k in dump_keys)
        else dump_keys
    )
    return [k for k in ret_keys_norm if k in box_keys_slim]


def plan_updates_from_dumps(
    data_path: Path,
    *,
    model: str,
    target: dict[str, Any],
    metadata_tools: dict[str, Any] | None,
    metadata_field_ttl: dict[str, Any] | None,
    sources: list[dict[str, Any]],
    req_keys: list[Any],
    req_fields: list[str],
    known_models: list[str],
) -> list[dict[str, Any]]:
    """
    dump 폴더 TTL 기반 갱신 계획.
    metadata.json 루트 tools·fields 로 필드별 tool_path·TTL 판별.
    response dump 는 status=SUCCESS 일 때만 필드를 커버한다.
    """
    if not req_keys or not req_fields:
        return []

    meta_keys = list(target.get("keys") or [])
    ret_keys_norm = [_normalize_key(k) for k in req_keys]
    mask = pd.DataFrame(False, index=ret_keys_norm, columns=req_fields)

    dump_paths = _list_model_dump_paths(data_path, model)

    for path in dump_paths:
        loaded = load_dump_payload(path)
        if loaded is None:
            continue
        records, meta = loaded
        is_response = meta.get("_kind") == "response" or path.name == "response.json"
        if not records and not is_response:
            continue

        ts_ms = dump_timestamp_ms(path, meta, known_models)
        tool_path = _resolve_dump_tool_path(path, meta, known_models)
        dump_keys = _keys_from_dump(path, meta, records, meta_keys)

        if is_response:
            if not _dump_response_succeeded(meta):
                continue
            tool_fields = _fields_for_tool(metadata_tools, tool_path)
            for field in req_fields:
                if tool_fields and field not in tool_fields:
                    continue
                field_tool = resolve_field_tool(metadata_tools, field, sources)
                if field_tool:
                    if slug_path(field_tool) != slug_path(tool_path) and tool_path:
                        continue
                ttl = resolve_field_ttl(metadata_field_ttl, field)
                if _is_expired(ts_ms, ttl):
                    continue

                common = _match_common_keys(meta_keys, ret_keys_norm, dump_keys)
                if common:
                    mask.loc[common, field] = True
            continue

        dump_fields = _infer_fields_from_records(
            records,
            meta_keys,
            _target_columns(target),
        )

        for field in req_fields:
            if field not in dump_fields:
                continue
            field_tool = resolve_field_tool(metadata_tools, field, sources)
            if field_tool:
                if slug_path(field_tool) != slug_path(tool_path) and tool_path:
                    continue
            ttl = resolve_field_ttl(metadata_field_ttl, field)
            if _is_expired(ts_ms, ttl):
                continue

            common = _match_common_keys(meta_keys, ret_keys_norm, dump_keys)
            if common:
                mask.loc[common, field] = True

    raw_plan = []
    for field in req_fields:
        missing_keys = mask.index[~mask[field]].tolist()
        if missing_keys:
            raw_plan.append({"keys": missing_keys, "field": field})

    if not raw_plan:
        return []

    df_plan = pd.DataFrame(raw_plan)
    df_plan["keys_tuple"] = df_plan["keys"].apply(
        lambda keys: tuple(_normalize_key(k) for k in keys)
    )
    grouped = df_plan.groupby("keys_tuple").agg({
        "keys": "first",
        "field": lambda x: list(x),
    }).reset_index(drop=True)

    return [{"keys": row["keys"], "fields": row["field"]} for _, row in grouped.iterrows()]


def cleanup_old_dumps(
    data_path: Path,
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    known_models: list[str] | None = None,
) -> int:
    """retention 초과 dump 삭제. TTL 참고용 최근 파일은 유지."""
    out_dir = dump_dir(data_path)
    if not out_dir.is_dir():
        return 0

    models = known_models or []
    if not models:
        for path in out_dir.glob("*.json"):
            parsed = re.match(r"^([A-Za-z][\w]*)-", path.name)
            if parsed and parsed.group(1) not in models:
                models.append(parsed.group(1))

    cutoff_ms = int((time.time() - retention_days * 86400) * 1000)
    deleted = 0
    candidates: list[Path] = list(out_dir.glob("*.json"))
    for model in models:
        model_dir = out_dir / model
        if model_dir.is_dir():
            candidates.extend(model_dir.rglob("*.json"))
    for path in sorted({p.resolve() for p in candidates}):
        loaded = load_dump_payload(path)
        if loaded is None:
            deleted += 1
            continue
        _, meta = loaded
        ts_ms = dump_timestamp_ms(path, meta, models)
        if ts_ms < cutoff_ms:
            path.unlink(missing_ok=True)
            deleted += 1
            parent = path.parent
            if parent.name not in (DUMP_DIR_NAME, *models) and not any(parent.iterdir()):
                parent.rmdir()

    if deleted:
        info(f"[PangeaDump] retention cleanup — removed {deleted} file(s) from {out_dir}")
    return deleted


def list_dump_files_for_model(data_path: Path, model: str) -> list[Path]:
    """model 에 해당하는 data dump 파일 (mtime 순). apply_pending_updates 용."""
    return sorted(
        [p for p in _list_model_dump_paths(data_path, model) if p.name != "response.json"],
        key=lambda p: p.stat().st_mtime,
    )
