"""Report layout — 프론트 렌더링용 blocks 트리 + root data 분리.

문서 모델
---------
보고서 JSON 은 두 축으로 나뉜다.

1. ``layout`` — 트리(rows/cols/card/…) + leaf 는 ``{"type", "key"}`` 만 가짐
2. ``data`` — leaf key → 실제 payload (echart option / table / text …)

이렇게 분리하는 이유: 동일 payload 를 여러 leaf 에서 참조·재배치할 수 있고,
프론트는 layout 만 walk 한 뒤 data[key] 로 바인딩하면 된다. 구 스키마는
block 안에 inline ``data`` / per-block ``catalog`` 를 넣었는데,
``finalize_report_document`` 가 hoist·strip 으로 새 계약에 맞춘다.

주요 흐름
---------
- ``add_block`` / ``layout_block``: narrative·visual codegen 이 layout leaf 생성
- ``discover_visual_keys`` + ``attach_catalog_visuals``: 칠판 catalog 에서
  chart/table 후보를 휴리스틱으로 찾아 data 에 정규화·부착
- ``build_report_document``: release/narrative 가 최종 root JSON 조립
- ``finalize_report_document``: 출고 직전 정규화 파이프라인(아래 함수 docstring)
"""

from __future__ import annotations

import re
from typing import Any

from .block_registry import chart_block_type, ensure_payload_role, table_block_type, validate_data_style
from .context import TaskContext

LayoutBlockType = str  # rows | cols | header | card | echart | table

def layout_block(
    *,
    type: LayoutBlockType,
    blocks: list[dict],
    style: dict[str, Any] | None = None,
) -> dict:
    """컨테이너 노드만 만든다 — payload 는 담지 않음 (children 은 blocks)."""
    node: dict[str, Any] = {"type": type, "blocks": blocks}
    if style:
        node["style"] = style
    return node

def add_block(
    data: dict[str, Any],
    *,
    type: LayoutBlockType,
    key: str,
    payload: Any,
    style: dict[str, Any] | None = None,
    data_style: dict[str, Any] | None = None,
    task_id: str | None = None,
    role: str | None = None,
    description: str | None = None,
) -> dict:
    """layout leaf 등록 — payload 는 root `data[key]` 에 저장 (description 포함).

    leaf 노드에는 key/type/style/task_id 만 두고, 무거운 payload 는 ``data`` dict
    에 side-effect 로 쓴다. description·data_style·role 은 payload 가 dict 일 때
    합쳐지며, 이미 있는 description 은 덮지 않는다(catalog 보강과 충돌 방지).
    """
    if isinstance(payload, dict):
        entry: Any = dict(payload)
        if description and "description" not in entry:
            entry["description"] = description
        if data_style:
            merged_style = dict(entry.get("style") or {})
            merged_style.update(data_style)
            entry["style"] = merged_style
    elif description:
        entry = {"value": payload, "description": description}
        if data_style:
            entry["style"] = dict(data_style)
    else:
        entry = payload
        if data_style and isinstance(entry, dict):
            merged_style = dict(entry.get("style") or {})
            merged_style.update(data_style)
            entry["style"] = merged_style
    entry = ensure_payload_role(entry, role)
    if isinstance(entry, dict) and "style" in entry:
        style_issues = validate_data_style(entry.get("style"))
        if style_issues:
            raise ValueError(f"data_style invalid for '{key}': {'; '.join(style_issues)}")
    data[key] = entry
    node: dict[str, Any] = {"type": type, "key": key}
    if style:
        node["style"] = style
    if task_id:
        node["task_id"] = task_id
    return node


def normalize_echart(raw: Any) -> dict[str, Any]:
    """다양한 visual 산출물을 프론트 echarts Option dict 로 수렴.

    허용 입력
    ---------
    1. ``{"type": "echarts", "value": {...}}`` — TaskContext 래핑 형태 → value
    2. 이미 Option 인 dict (``series`` 또는 ``xAxis`` 존재) — 그대로 반환

    그 외(문자열 HTML, pyecharts 객체 직렬화 등)는 ValueError.
    attach_catalog_visuals 는 이 예외를 catch 해서 해당 key 를 skip 한다 —
    catalog 휴리스틱이 false positive 일 수 있기 때문.
    """
    if isinstance(raw, dict):
        if raw.get("type") == "echarts" and isinstance(raw.get("value"), dict):
            return raw["value"]
        if "series" in raw or "xAxis" in raw:
            return raw
    raise ValueError("echart payload 형식 아님")


def normalize_table(raw: Any) -> dict[str, Any]:
    """레코드 배열·래핑 dict 를 ``{header, dtypes, data}`` 계약으로 정규화.

    이미 계약 형태면 identity. 아니면
    - ``{"type":"table","value":[...]}`` / ``{"value":[...]}`` / bare list
      에서 rows 를 뽑고,
    - 첫 row 의 키로 header, 값 타입으로 dtypes 를 추정한다.

    edge cases
    ----------
    - 빈 rows → 빈 테이블(에러 아님) — visual 이 placeholder 를 남긴 경우 허용
    - row 가 dict 가 아니면 실패(리스트-of-list 미지원)
    - bool 을 int 보다 먼저 검사 — Python 에서 bool ⊂ int 이므로 순서 중요
    - float decimals=1 은 표시용 기본값(프론트 포맷 힌트)
    """
    if isinstance(raw, dict) and {"header", "dtypes", "data"} <= raw.keys():
        return raw

    rows: list[Any] = []
    if isinstance(raw, dict):
        if raw.get("type") == "table" and isinstance(raw.get("value"), list):
            rows = raw["value"]
        elif isinstance(raw.get("value"), list):
            rows = raw["value"]
    elif isinstance(raw, list):
        rows = raw

    if not rows:
        return {"header": [], "dtypes": {}, "data": []}

    if not isinstance(rows[0], dict):
        raise ValueError("table row 는 dict record 배열이어야 함")

    columns = list(rows[0].keys())
    dtypes: dict[str, Any] = {}
    for col in columns:
        sample = rows[0][col]
        if isinstance(sample, bool):
            dtypes[col] = {"type": "boolean"}
        elif isinstance(sample, int):
            dtypes[col] = {"type": "integer"}
        elif isinstance(sample, float):
            dtypes[col] = {"type": "number", "decimals": 1}
        else:
            dtypes[col] = {"type": "string"}

    return {"header": columns, "dtypes": dtypes, "data": rows}

def _catalog_key_specs(catalog: dict[str, Any], task_id: str) -> dict[str, Any]:
    """ctx.catalog keys — dict 또는 list 모두 허용."""
    keys = (catalog.get(task_id) or {}).get("keys") or {}
    if isinstance(keys, dict):
        return keys
    return {k: {} for k in keys}

def catalog_key_description(catalog: dict[str, Any], task_id: str, key: str) -> str | None:
    spec = _catalog_key_specs(catalog, task_id).get(key) or {}
    desc = spec.get("description") if isinstance(spec, dict) else None
    return desc or None

def simplify_report_tasks(catalog: dict[str, Any]) -> dict[str, Any]:
    """report.tasks — task_id → {status, keys: [key, ...]}."""
    out: dict[str, Any] = {}
    for tid, info in catalog.items():
        keys = info.get("keys") or {}
        if isinstance(keys, dict):
            key_list = sorted(keys.keys())
        else:
            key_list = list(keys)
        out[tid] = {"status": info.get("status", "success"), "keys": key_list}
    return out

def _is_full_task_catalog(tasks: dict[str, Any]) -> bool:
    return any(isinstance(info.get("keys"), dict) for info in tasks.values())

def discover_visual_keys(
    catalog: dict[str, Any],
    *,
    task_ids: list[str] | None = None,
) -> list[tuple[str, str, str]]:
    """catalog 에서 echart/table 후보 (task_id, key, block_type) 목록.

    휴리스틱 (우선순위)
    -------------------
    1. ``spec.block_type`` 이 echart/chart/table — visual 태스크가 명시한 힌트
    2. key+description 텍스트에 chart/scatter/line/bar/pie → echart
    3. "table" 포함 또는 key 접미사 ``_table`` / ``_view`` → table

    필터
    ----
    - ``spec.type`` 이 있고 ``json`` 이 아니면 skip — parquet 등 비렌더 산출 제외
    - ``task_ids`` 가 주어지면 해당 upstream 만 (release 가 context 로 제한할 때)

    오탐이 있어도 attach 단계에서 normalize 실패 시 skip 하므로, 여기선
    recall 을 조금 높게 잡는 편이 안전하다(하드코딩 key 목록을 안 쓰기 위함).
    """
    found: list[tuple[str, str, str]] = []
    for tid, info in catalog.items():
        if task_ids is not None and tid not in task_ids:
            continue
        for key, spec in _catalog_key_specs(catalog, tid).items():
            if isinstance(spec, dict):
                key_type = spec.get("type")
                if key_type is not None and key_type != "json":
                    continue
                desc = spec.get("description") or ""
                block_type_hint = (spec.get("block_type") or "").lower()
            else:
                desc = ""
                block_type_hint = ""
            blob = f"{key} {desc}".lower()
            if block_type_hint == "echart" or block_type_hint == "chart":
                found.append((tid, key, "echart"))
            elif block_type_hint == "table":
                found.append((tid, key, "table"))
            elif any(m in blob for m in ("echart", "chart", "scatter", "line", "bar", "pie")):
                found.append((tid, key, "echart"))
            elif "table" in blob or key.endswith("_table") or key.endswith("_view"):
                found.append((tid, key, "table"))
    return found


def attach_catalog_visuals(
    ctx: TaskContext,
    catalog: dict[str, Any],
    data: dict[str, Any],
    *,
    task_ids: list[str] | None = None,
) -> list[dict]:
    """upstream catalog 기준 visual 블록 생성 — key 이름 하드코딩 금지.

    데이터 흐름
    -----------
    discover_visual_keys → ctx.get_result(tid, key) → normalize_* →
    block_registry 로 leaf type/role 부여 → add_block(data, ...) → leaf 목록 반환.

    chart_idx / table_idx 는 1부터 증가하며 ``chart_block_type`` /
    ``table_block_type`` 이 역할(primary/secondary …)을 나눌 때 사용한다.
    normalize 실패·None 결과는 continue — 휴리스틱 오탐을 layout 에 넣지 않음.
    """
    blocks: list[dict] = []
    chart_idx = 0
    table_idx = 0
    for tid, key, block_type in discover_visual_keys(catalog, task_ids=task_ids):
        raw = ctx.get_result(tid, key)
        if raw is None:
            continue
        try:
            if block_type == "echart":
                chart_idx += 1
                leaf_type, data_role = chart_block_type(chart_idx)
                payload = normalize_echart(raw)
            else:
                table_idx += 1
                leaf_type, data_role = table_block_type(table_idx, key)
                payload = normalize_table(raw)
        except ValueError:
            continue
        if isinstance(payload, dict) and "role" not in payload:
            payload = dict(payload)
            payload["role"] = data_role
        blocks.append(
            add_block(
                data,
                type=leaf_type,
                key=key,
                payload=payload,
                role=data_role,
                task_id=tid,
                description=catalog_key_description(catalog, tid, key),
            )
        )
    return blocks

def build_report_document(
    *,
    title: str,
    description: str,
    template_id: str,
    plan_id: str,
    did: str,
    rid: str,
    tasks: dict[str, Any],
    layout_blocks: list[dict] | None = None,
    layout: list[dict] | None = None,
    data: dict[str, Any],
    root_style: dict[str, Any] | None = None,
    layout_type: str = "rows",
    version: int = 1,
) -> dict:
    """release 태스크 산출 — 보고서 root JSON.

    ``layout=`` 는 ``layout_blocks=`` LLM 별칭 (blocks 리스트).
    """
    blocks = layout_blocks if layout_blocks is not None else layout
    if blocks is None:
        raise ValueError("build_report_document: layout_blocks= (또는 layout=) 필수")
    layout_root: dict[str, Any] = {
        "type": layout_type,
        "blocks": blocks,
    }
    if root_style:
        layout_root["style"] = root_style
    task_index = simplify_report_tasks(tasks) if _is_full_task_catalog(tasks) else tasks
    return {
        "title": title,
        "description": description,
        "template_id": template_id,
        "version": version,
        "plan_id": plan_id,
        "did": did,
        "rid": rid,
        "layout": layout_root,
        "data": data,
        "tasks": task_index,
    }

def _hoist_inline_block_data(blocks: list[dict], data: dict[str, Any]) -> None:
    """구 스키마: layout leaf 안에 있던 inline data 를 root data 로 끌어올림.

    setdefault — 이미 root 에 같은 key 가 있으면 leaf 쪽을 버리지 않고 유지
    (release patch 가 root 를 우선한 경우를 존중).
    """
    for block in blocks:
        nested = block.get("blocks")
        if isinstance(nested, list):
            _hoist_inline_block_data(nested, data)
        inline = block.get("data")
        if isinstance(inline, dict):
            for key, payload in inline.items():
                data.setdefault(key, payload)
            block.pop("data", None)

def _strip_block_catalog(blocks: list[dict]) -> None:
    """layout leaf/block 에서 per-block catalog 제거 (루트 tasks 만 사용)."""
    for block in blocks:
        nested = block.get("blocks")
        if isinstance(nested, list):
            _strip_block_catalog(nested)
        block.pop("catalog", None)

def _walk_layout_leaves(blocks: list[dict]) -> list[dict]:
    leaves: list[dict] = []
    for block in blocks:
        nested = block.get("blocks")
        if isinstance(nested, list):
            leaves.extend(_walk_layout_leaves(nested))
        elif block.get("key"):
            leaves.append(block)
    return leaves

_DRAFT_SUFFIX = re.compile(r"\s*(보고서\s*)?초안\s*$", re.I)


def _strip_draft_markers(text: str) -> str:
    cleaned = _DRAFT_SUFFIX.sub("", text.strip()).strip()
    return cleaned


def _document_title_text(data: dict[str, Any], layout: dict[str, Any]) -> str | None:
    blocks = layout.get("blocks")
    if not isinstance(blocks, list):
        return None
    for leaf in _walk_layout_leaves(blocks):
        if leaf.get("type") not in {"document_title", "header"}:
            continue
        key = leaf.get("key")
        if not key or key not in data:
            continue
        payload = data[key]
        if isinstance(payload, dict):
            text = payload.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def _sanitize_report_meta(
    doc: dict[str, Any],
    *,
    fallback_title: str = "",
    fallback_description: str = "",
) -> None:
    """루트 title/description 정리 — 초안 문구·document_title 이중 표기 방지."""
    data = doc.get("data") if isinstance(doc.get("data"), dict) else {}
    layout = doc.get("layout") if isinstance(doc.get("layout"), dict) else {}
    block_title = _document_title_text(data, layout) if data and layout else None

    title = str(doc.get("title") or fallback_title or "").strip()
    if block_title:
        title = block_title
    elif title:
        title = _strip_draft_markers(title)
    if title:
        doc["title"] = title

    desc = str(doc.get("description") or fallback_description or "").strip()
    desc = _strip_draft_markers(desc)
    if desc and title and desc == title:
        desc = ""
    if desc and title and desc.endswith(title):
        desc = desc[: -len(title)].strip(" -—·:")
        desc = _strip_draft_markers(desc)
    if desc and ("초안" in desc or len(desc) > 120):
        desc = ""
    if desc:
        doc["description"] = desc
    elif "description" in doc:
        doc.pop("description", None)


def _enrich_data_descriptions(
    data: dict[str, Any],
    layout: dict[str, Any],
    task_catalog: dict[str, Any],
) -> None:
    """layout leaf key + task_catalog → data[key].description 보강."""
    blocks = layout.get("blocks")
    if not isinstance(blocks, list) or not task_catalog:
        return
    for leaf in _walk_layout_leaves(blocks):
        key = leaf.get("key")
        tid = leaf.get("task_id")
        if not key or key not in data or not tid:
            continue
        desc = catalog_key_description(task_catalog, tid, key)
        if not desc:
            continue
        entry = data[key]
        if isinstance(entry, dict) and "description" not in entry:
            patched = dict(entry)
            patched["description"] = desc
            data[key] = patched

def finalize_report_document(
    doc: dict[str, Any],
    *,
    tasks: dict[str, Any] | None = None,
    task_catalog: dict[str, Any] | None = None,
    catalog: dict[str, Any] | None = None,
    plan_id: str,
    did: str,
    rid: str,
    title: str = "",
    description: str = "",
    template_id: str = "default",
) -> dict[str, Any]:
    """루트 필드·data/tasks 보강, 구 스키마 inline data hoist.

    출고(release) 직전 정규화 파이프라인 — 단계 순서대로:

    1. full_board 결정
       ``task_catalog or catalog or tasks`` , 없으면 구 스키마 ``doc["catalog"]``.
       (인자 이름이 여러 개인 이유: narrative/release codegen 호출 스타일 혼재)
    2. layout.blocks walk
       - ``_hoist_inline_block_data``: block["data"] → root data (setdefault, 덮지 않음)
       - ``_strip_block_catalog``: per-block catalog 제거 (루트 tasks 만 유효)
       - layout.type 기본 ``rows``
       - ``_enrich_data_descriptions``: leaf.task_id + board description 보강
    3. 루트 메타 setdefault(plan_id/did/rid/template/version) + ``_sanitize_report_meta``
       (초안·document_title 이중 표기·title==description 제거)
    4. 루트 ``catalog`` 키 삭제, ``tasks`` 를 simplify_report_tasks 로 compact 인덱스화

    반환 doc 은 동일 객체를 mutate 후 반환 — 호출측이 재할당해도 안전.
    """
    full_board = task_catalog or catalog or tasks or {}
    legacy_root_catalog = doc.get("catalog")
    if not full_board and legacy_root_catalog:
        full_board = legacy_root_catalog
    data: dict[str, Any] = dict(doc.get("data") or {})
    layout = doc.get("layout") or {}
    if isinstance(layout, dict):
        blocks = layout.get("blocks")
        if isinstance(blocks, list):
            _hoist_inline_block_data(blocks, data)
            _strip_block_catalog(blocks)
        if not layout.get("type"):
            layout["type"] = "rows"
        _enrich_data_descriptions(data, layout, full_board)

    doc.setdefault("title", title)
    doc.setdefault("description", description)
    _sanitize_report_meta(doc, fallback_title=title, fallback_description=description)
    doc.setdefault("template_id", template_id)
    doc.setdefault("version", 1)
    doc.setdefault("plan_id", plan_id)
    doc.setdefault("did", did)
    doc.setdefault("rid", rid)
    doc["layout"] = layout
    doc["data"] = data
    doc.pop("catalog", None)
    if full_board:
        doc["tasks"] = simplify_report_tasks(full_board)
    elif not doc.get("tasks"):
        legacy_tasks = doc.get("tasks") or {}
        doc["tasks"] = (
            simplify_report_tasks(legacy_tasks)
            if _is_full_task_catalog(legacy_tasks)
            else legacy_tasks
        )
    return doc
