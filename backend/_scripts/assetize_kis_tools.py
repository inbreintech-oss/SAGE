#!/usr/bin/env python3
"""Assetize KIS investor + stock-info tools."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from sage.db import saged
from sage.models import doc
from sage.tool.assetize import perform_assetize
from sage.tool.metadata import read_metadata, write_metadata


async def _kis_secret_id(user_id: str = "admin") -> str | None:
    wanted = "kis"
    exact = await saged.load_secret_by_provider(user_id, wanted)
    if exact:
        return exact.secret_id
    for record in await saged.list_secrets(user_id):
        if (record.provider or "").strip().lower() == wanted:
            return record.secret_id
    return None

ASSETS = [
    {
        "tool_id": "tm-kis-investor-inquiry-f1a2b3c4",
        "asset_path": "kis/investor",
        "title": "KIS 투자자 수급",
        "description": "기관·외국인 순매수 수급 조회 (FHKST01010900)",
        "category": "stock",
    },
    {
        "tool_id": "tm-kis-stock-basic-info-d4e5f6a7",
        "asset_path": "kis/stock-info",
        "title": "KIS 주식기본조회",
        "description": "종목 업종 중분류(idx_bztp_mcls_cd_name) 조회 (CTPF1002R)",
        "category": "stock",
    },
]


async def _patch_tool_meta(path: str, *, category: str | None, secret_id: str | None) -> None:
    col = saged.get_collection(doc.Tool)
    raw = await col.find_one({"_id": path}) or await col.find_one({"tool_id": path})
    if not raw:
        print(f"[WARN] DB record not found for {path}")
        return
    tool = doc.Tool.model_validate(saged._read(raw))
    if category:
        tool.category = category
    if secret_id:
        tool.secret_id = secret_id
    await saged.save(tool)

    meta = read_metadata(path) or {}
    write_metadata(
        path,
        status=meta.get("status") or tool.status or "assetized",
        instructions=meta.get("instructions", ""),
        extra={
            k: v
            for k, v in {
                "description": meta.get("description") or tool.description,
                "query_examples": meta.get("query_examples") or tool.query_examples,
                "secret_id": secret_id or meta.get("secret_id") or tool.secret_id,
            }.items()
            if v
        },
    )


async def main() -> int:
    kis_secret_id = await _kis_secret_id()
    if kis_secret_id:
        print(f"[OK] bound secret_id={kis_secret_id} (provider=kis)")
    else:
        print("[WARN] no SecretKey with provider=kis")

    for item in ASSETS:
        asset_path = item["asset_path"]
        meta = Path(ROOT / "tools" / asset_path.replace("/", "\\") / "metadata.json")
        if meta.is_file() and '"status": "assetized"' in meta.read_text(encoding="utf-8"):
            print(f"[SKIP] already assetized: {asset_path}")
        else:
            asset_path = await perform_assetize(
                saged,
                tool_id=item["tool_id"],
                asset_path=item["asset_path"],
                title=item["title"],
                description=item["description"],
            )
            print(f"[OK] assetized -> {asset_path}")
        await _patch_tool_meta(
            item["asset_path"],
            category=item.get("category"),
            secret_id=kis_secret_id,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
