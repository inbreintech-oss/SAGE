"""도구 자산화 — 파일/metadata/DB 일괄 처리."""

from __future__ import annotations

import shutil
from pathlib import Path

from sage import tool as tools
from sage.config import TOOLS_DIR
from sage.db import SAGEDataStore
from sage.models import doc
from sage.models.doc import ToolStatus
from sage.models.tool import ToolPack
from sage.tool.metadata import read_metadata, tool_dir, write_metadata, is_assetized
from sage.mcp.client import warmup_mcp_tool


def _resolve_source_path(*, tool_id: str | None, tool_path: str | None) -> str:
    """tm-* (generate 결과) 또는 kis/stock 같은 기존 경로 중 하나를 소스로 확정."""
    if tool_id:
        return tool_id
    if tool_path:
        return tool_path
    raise ValueError("tool_id 또는 tool_path 중 하나는 필수입니다.")


async def perform_assetize(
    db: SAGEDataStore,
    *,
    tool_id: str | None = None,
    asset_path: str | None = None,
    tool_path: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> str:
    """
    도구를 assetized 상태로 등록합니다.
    Returns: 최종 asset_path (MCP HTTP 경로)
    """
    source_path = _resolve_source_path(tool_id=tool_id, tool_path=tool_path)
    # asset_path 미지정 시 소스와 동일 경로에 in-place assetize
    final_path = asset_path or source_path

    source_dir = tool_dir(source_path)
    main_py = source_dir / "main.py"
    if not main_py.is_file():
        raise FileNotFoundError(f"도구 main.py 를 찾을 수 없습니다: {source_path}")

    content = main_py.read_text(encoding="utf-8")
    dest_dir = tool_dir(final_path)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if source_dir.resolve() != dest_dir.resolve():
        # tm-* → kis/stock 승격: main/caller 를 목적지로 복사
        shutil.copy2(main_py, dest_dir / "main.py")
        caller = source_dir / "caller.py"
        if caller.is_file():
            shutil.copy2(caller, dest_dir / "caller.py")

    existing_meta = read_metadata(final_path) or read_metadata(source_path) or {}
    existing_tool = None
    if tool_id:
        existing_tool = await db.load(doc.Tool, tool_id)

    secret_id = None
    if existing_tool and existing_tool.secret_id:
        secret_id = existing_tool.secret_id
    if not secret_id:
        secret_id = existing_meta.get("secret_id") or None
    if not secret_id:
        col = db.get_collection(doc.Tool)
        dest_raw = await col.find_one({"_id": final_path}) or await col.find_one({"tool_id": final_path})
        secret_id = (dest_raw or {}).get("secret_id") or None

    resolved_title = title or (existing_tool.title if existing_tool else None) or final_path.replace("/", " ")
    resolved_description = description
    if resolved_description is None and existing_tool:
        resolved_description = existing_tool.description

    status: ToolStatus = "assetized"
    pack = ToolPack(
        tool_id=final_path,
        title=resolved_title,
        description=resolved_description,
        code=content,
        caller=(dest_dir / "caller.py").read_text(encoding="utf-8")
        if (dest_dir / "caller.py").is_file()
        else None,
        query_examples=list(existing_tool.query_examples) if existing_tool and existing_tool.query_examples else [],
    )
    tools.dump(pack, status=status, target="code", base_dir=TOOLS_DIR)

    # metadata.json — status=assetized 이면 MCP 게이트웨이 HTTP mount 대상
    raw_extra = {
        "query_examples": pack.query_examples,
        "description": pack.description,
        "secret_id": secret_id,
    }
    extra = {k: v for k, v in raw_extra.items() if v}
    write_metadata(
        final_path,
        status=status,
        instructions=existing_meta.get("instructions", ""),
        extra=extra or None,
    )

    # sav. doc
    tool_doc = doc.Tool(
        tool_id=final_path,
        title=resolved_title,
        description=resolved_description,

        code=content,
        caller=pack.caller,

        query_examples=pack.query_examples,
        category=existing_tool.category if existing_tool else None,
        tags=existing_tool.tags if existing_tool else None,
        query=existing_tool.query if existing_tool else None,
        secret_id=secret_id,
        status=status
    )
    await db.save(tool_doc)

    # 경로가 바뀌면 이전 tm-* DB 레코드 삭제 (중복 목록 방지)
    if tool_id and tool_id != final_path:
        await db.delete(tool_id)

    # MCP 세션·lazy mount 워밍업 — 첫 call 지연 감소
    await warmup_mcp_tool(final_path)

    return final_path

