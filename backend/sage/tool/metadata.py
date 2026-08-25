"""도구 metadata.json 읽기/쓰기 (MCP/client 전용 — 순환 import 방지)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, get_args

from sage.config import TOOLS_DIR
from sage.models.doc import ToolStatus


def tool_dir(path: str) -> Path:
    """tools/ 하위 경로 — 슬래시·백슬래시 혼용을 OS 경로로 정규화."""
    from sage.config import resolve_narratix_home

    tools = resolve_narratix_home() / "tools"
    normalized = path.strip().lstrip("/").replace("\\", "/")
    if not normalized:
        return tools
    return tools.joinpath(*normalized.split("/"))


def metadata_path(path: str) -> Path:
    return tool_dir(path) / "metadata.json"


def read_metadata(path: str) -> dict[str, Any] | None:
    meta_file = metadata_path(path)
    if not meta_file.is_file():
        return None
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def tool_status(path: str) -> ToolStatus | None:
    meta = read_metadata(path)
    if not meta:
        return None
    status = meta.get("status")
    if status in get_args(ToolStatus):
        return status
    return None


def is_assetized(path: str) -> bool:
    """status=assetized → MCP HTTP(8091) transport. 미만이면 stdio main.py 직접 실행."""
    return tool_status(path) == "assetized"


def write_metadata(
    path: str,
    *,
    status: ToolStatus,
    instructions: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    tool_path = tool_dir(path)
    tool_path.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        # "id": path,
        "tool_id": path,
        "status": status,
        "instructions": instructions,
        "created_at": datetime.now().isoformat(),
    }
    if extra:
        payload.update(extra)
    meta_file = tool_path / "metadata.json"
    if meta_file.is_file():
        try:
            existing = json.loads(meta_file.read_text(encoding="utf-8"))
            # upsert 시 최초 created_at 유지
            payload["created_at"] = existing.get("created_at", payload["created_at"])
            # dump() 가 extra 없이 덮어써도 도구에 묶인 secret_id 유지
            if existing.get("secret_id") and not payload.get("secret_id"):
                payload["secret_id"] = existing["secret_id"]
        except (OSError, json.JSONDecodeError):
            pass
    meta_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
