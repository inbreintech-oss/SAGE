"""ReportDocument 구성 품질 lint — data.role + type 세분화 (3안)."""

from __future__ import annotations

import re
from typing import Any

from .block_registry import (
    PATTERN_REQUIRED_ROLES,
    _CARD_TYPES,
    _SUMMARY_ROLES,
    is_known_role,
    resolve_role,
    role_allowed_for_type,
    validate_data_style,
)
from .layout import _walk_layout_leaves

_BOILERPLATE = re.compile(r"본 보고서는 최종 검토", re.I)
_TASK_ID_IN_TEXT = re.compile(r"\btask[-_][\w-]+\b", re.I)
_UNICODE_SPACE = re.compile(r"[\u2000-\u200b\u202f\u205f\u3000]")
_HANGUL = re.compile(r"[가-힣]")


def _echart_has_series(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    option = payload.get("option") if isinstance(payload.get("option"), dict) else payload
    if not isinstance(option, dict):
        return False
    series = option.get("series")
    if not isinstance(series, list) or len(series) == 0:
        return False
    for s in series:
        if isinstance(s, dict) and s.get("data"):
            return True
    return False


def _table_has_rows(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    rows = payload.get("data") or payload.get("rows")
    return isinstance(rows, list) and len(rows) > 0


def _table_header_unmappable(payload: Any) -> bool:
    """header 길이가 행 키/dtypes 와 달라 인덱스 매핑이 불가할 때만 True.

    한글 표시 라벨(header[i] ≠ data 키)은 table_spec 정상 패턴이다.
    """
    if not isinstance(payload, dict):
        return False
    columns = payload.get("columns")
    if isinstance(columns, list) and columns:
        return False
    header = payload.get("header")
    rows = payload.get("data") or payload.get("rows")
    if not isinstance(header, list) or not header or not isinstance(rows, list) or not rows:
        return False
    if not isinstance(rows[0], dict):
        return False
    row_keys = list(rows[0].keys())
    dtype_keys = list((payload.get("dtypes") or {}).keys()) if isinstance(payload.get("dtypes"), dict) else []
    if len(header) == len(row_keys) or (dtype_keys and len(header) == len(dtype_keys)):
        return False
    row_key_set = set(row_keys)
    return not all(isinstance(h, str) and h in row_key_set for h in header)


def _table_header_not_localized(payload: Any) -> bool:
    """header 가 data 영문 필드명과 동일 — 독자용 한글 라벨이 아님."""
    if not isinstance(payload, dict):
        return False
    columns = payload.get("columns")
    if isinstance(columns, list):
        labels = []
        for col in columns:
            if isinstance(col, dict):
                labels.append(str(col.get("label") or col.get("title") or col.get("name") or ""))
            elif isinstance(col, str):
                labels.append(col)
        if labels and any(re.search(r"[가-힣]", lab) for lab in labels):
            return False
    header = payload.get("header")
    rows = payload.get("data") or payload.get("rows")
    if not isinstance(header, list) or not header or not isinstance(rows, list) or not rows:
        return False
    if not isinstance(rows[0], dict):
        return False
    row_keys = set(rows[0].keys())
    if not all(isinstance(h, str) and h in row_keys for h in header):
        return False
    return all(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", h or "") is not None for h in header)


def _echart_option(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    option = payload.get("option") if isinstance(payload.get("option"), dict) else payload
    return option if isinstance(option, dict) else None


def _echart_has_multigrid(payload: Any) -> bool:
    """프론트가 grid 배열을 단일 object 로 접어 차트가 소실된다."""
    option = _echart_option(payload)
    if not option:
        return False
    grid = option.get("grid")
    if isinstance(grid, list) and len(grid) > 1:
        return True
    if any(
        isinstance(s, dict) and s.get("gridIndex") not in (None, 0)
        for s in (option.get("series") or [])
        if isinstance(s, dict)
    ):
        return True
    return False


def _iter_series_numbers(option: dict[str, Any]) -> list[float]:
    nums: list[float] = []
    for s in option.get("series") or []:
        if not isinstance(s, dict):
            continue
        data = s.get("data")
        if not isinstance(data, list):
            continue
        for item in data:
            if isinstance(item, (int, float)):
                nums.append(float(item))
            elif isinstance(item, dict) and isinstance(item.get("value"), (int, float)):
                nums.append(float(item["value"]))
            elif isinstance(item, (list, tuple)) and item and isinstance(item[-1], (int, float)):
                nums.append(float(item[-1]))
    return nums


def _echart_has_zeroline(option: dict[str, Any]) -> bool:
    def _mark_has_zero(mark: Any) -> bool:
        if not isinstance(mark, dict):
            return False
        for item in mark.get("data") or []:
            if not isinstance(item, dict):
                continue
            if item.get("xAxis") in (0, 0.0, "0") or item.get("yAxis") in (0, 0.0, "0"):
                return True
        return False

    if _mark_has_zero(option.get("markLine")):
        return True
    for s in option.get("series") or []:
        if isinstance(s, dict) and _mark_has_zero(s.get("markLine")):
            return True
    return False


def _echart_signed_bar_missing_zeroline(payload: Any) -> bool:
    option = _echart_option(payload)
    if not option:
        return False
    series = option.get("series") or []
    if not any(isinstance(s, dict) and s.get("type") == "bar" for s in series):
        return False
    nums = _iter_series_numbers(option)
    if not nums:
        return False
    if min(nums) >= 0 or max(nums) <= 0:
        return False
    return not _echart_has_zeroline(option)


def _card_plain_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    parts = []
    for field in ("title", "content", "text"):
        val = payload.get(field)
        if isinstance(val, str):
            parts.append(val)
    return "\n".join(parts)


def _thin_insight_text(payload: Any) -> bool:
    text = _card_plain_text(payload)
    if not text.strip():
        return True
    if len(text.strip()) < 80:
        return True
    if re.search(r"데이터가 보여|분석 결과입니다|시각화 결과", text):
        return True
    if not re.search(r"\d", text):
        return True
    return False


def _thin_executive_text(payload: Any) -> bool:
    text = _card_plain_text(payload)
    if len(text.strip()) < 40:
        return True
    if not re.search(r"\d", text):
        return True
    return False


def _card_bullet_count(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    content = payload.get("content")
    if not isinstance(content, str):
        return 0
    return len(re.findall(r"^\s*[-*]\s+", content, re.M))


def _duplicate_title_heading(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    title = payload.get("title")
    content = payload.get("content")
    if not isinstance(title, str) or not isinstance(content, str):
        return False
    t = title.strip().lstrip("#").strip()
    for line in content.splitlines():
        m = re.match(r"^#+\s*(.+)", line.strip())
        if m and m.group(1).strip() == t:
            return True
    return False


def _is_card_type(block_type: str) -> bool:
    return block_type in _CARD_TYPES


def _is_chart_type(block_type: str) -> bool:
    return block_type in {"echart", "chart", "primary_chart", "secondary_chart"}


def _visible_text_fields(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    out: list[str] = []
    for field in ("text", "title", "content"):
        val = payload.get(field)
        if isinstance(val, str) and val.strip():
            out.append(val)
    return out


def _hangul_stripped(text: str) -> bool:
    """Korean body replaced by unicode spaces (release tofu)."""
    if not isinstance(text, str) or len(text) < 8:
        return False
    tofu = len(_UNICODE_SPACE.findall(text))
    hangul = len(_HANGUL.findall(text))
    letters = len(re.findall(r"[A-Za-z가-힣]", text))
    if tofu >= 8 and hangul < 4:
        return True
    if tofu >= 12 and letters < 8:
        return True
    return False


def _payload_hangul_stripped(payload: Any) -> bool:
    texts = list(_visible_text_fields(payload))
    option = _echart_option(payload)
    if option:
        title = option.get("title")
        if isinstance(title, list) and title:
            title = title[0]
        if isinstance(title, dict):
            for key in ("text", "subtext"):
                val = title.get(key)
                if isinstance(val, str):
                    texts.append(val)
    if isinstance(payload, dict):
        for field in ("text", "title", "content"):
            val = payload.get(field)
            if isinstance(val, str):
                texts.append(val)
    return any(_hangul_stripped(t) for t in texts)


def _task_boundary_visible(payload: Any) -> bool:
    return any(_TASK_ID_IN_TEXT.search(text) for text in _visible_text_fields(payload))


def _is_table_type(block_type: str) -> bool:
    return block_type in {"table", "metrics_table", "appendix_table"}


def lint_report_document(doc: dict[str, Any]) -> dict[str, Any]:
    """구성 품질 점검 — score 0~100, issues[], passed."""
    issues: list[dict[str, str]] = []
    data: dict[str, Any] = dict(doc.get("data") or {})
    layout = doc.get("layout") or {}
    blocks = layout.get("blocks") if isinstance(layout, dict) else []
    leaves = _walk_layout_leaves(blocks) if isinstance(blocks, list) else []

    score = 100
    roles_present: set[str] = set()
    chart_keys: list[str] = []
    table_keys: list[str] = []
    leaf_sequence: list[tuple[str, str, str | None]] = []

    for leaf in leaves:
        key = leaf.get("key")
        if not key:
            continue
        btype = str(leaf.get("type") or "")
        layout_role = leaf.get("role") if isinstance(leaf.get("role"), str) else None

        if key not in data:
            issues.append({
                "level": "error",
                "code": "missing_data_key",
                "message": f"layout key '{key}' 에 대응하는 data 없음",
                "key": key,
            })
            score -= 15
            continue

        payload = data[key]
        role = resolve_role(payload, btype, layout_role=layout_role)
        if _payload_hangul_stripped(payload):
            issues.append({
                "level": "error",
                "code": "hangul_stripped",
                "message": f"'{key}' 한글이 유니코드 공백으로 비어 있음 — 출판본이 깨짐",
                "key": key,
                "role": role or "",
            })
            score -= 30
        if role:
            roles_present.add(role)

        if role and not is_known_role(role):
            issues.append({
                "level": "warning",
                "code": "unknown_role",
                "message": f"알 수 없는 data.role '{role}'",
                "key": key,
                "role": role,
            })
            score -= 5
        elif role and not role_allowed_for_type(btype, role):
            issues.append({
                "level": "warning",
                "code": "type_role_mismatch",
                "message": f"type '{btype}' 에 role '{role}' 조합 불일치",
                "key": key,
                "role": role,
            })
            score -= 8

        if isinstance(payload, dict):
            style_issues = validate_data_style(payload.get("style"))
            for msg in style_issues:
                issues.append({
                    "level": "info",
                    "code": "data_style_invalid",
                    "message": f"data '{key}' style: {msg}",
                    "key": key,
                    "role": role or "",
                })
                score -= 2

        leaf_sequence.append((btype, key, role))

        if _is_chart_type(btype):
            chart_keys.append(key)
            if not _echart_has_series(payload):
                issues.append({
                    "level": "warning",
                    "code": "empty_chart_series",
                    "message": f"chart '{key}' series 비어 있음",
                    "key": key,
                    "role": role or "",
                })
                score -= 8
            if _echart_has_multigrid(payload):
                issues.append({
                    "level": "warning",
                    "code": "chart_multigrid",
                    "message": (
                        f"chart '{key}' 가 grid 배열/gridIndex 서브플롯 — "
                        "단일 grid 로 접거나 차트를 2개로 나눌 것 (프론트에서 미표시)"
                    ),
                    "key": key,
                    "role": role or "",
                })
                score -= 10
            if _echart_signed_bar_missing_zeroline(payload):
                issues.append({
                    "level": "warning",
                    "code": "chart_missing_zeroline",
                    "message": (
                        f"chart '{key}' 양·음 bar 인데 0선 markLine 없음"
                    ),
                    "key": key,
                    "role": role or "",
                })
                score -= 6

        if _is_table_type(btype) and not _table_has_rows(payload):
            issues.append({
                "level": "warning",
                "code": "empty_table",
                "message": f"table '{key}' 행 없음",
                "key": key,
                "role": role or "",
            })
            score -= 8
        elif _is_table_type(btype):
            table_keys.append(key)
            if _table_header_unmappable(payload):
                issues.append({
                    "level": "warning",
                    "code": "table_header_key_mismatch",
                    "message": (
                        f"table '{key}' header 길이가 data 행 키와 달라 매핑 불가 — "
                        "header 는 한글 라벨, dtypes/data 키는 영문, 길이를 맞출 것"
                    ),
                    "key": key,
                    "role": role or "",
                })
                score -= 6
            elif _table_header_not_localized(payload):
                issues.append({
                    "level": "warning",
                    "code": "table_header_not_localized",
                    "message": (
                        f"table '{key}' header 가 영문 필드명과 동일 — "
                        "한글 표시 라벨(header 또는 columns[].label) 필요"
                    ),
                    "key": key,
                    "role": role or "",
                })
                score -= 6

        if btype in {"document_title", "header"} and isinstance(payload, dict):
            text = payload.get("text")
            if isinstance(text, str) and re.search(r"초안", text):
                issues.append({
                    "level": "warning",
                    "code": "draft_in_title",
                    "message": f"제목 '{key}' 에 '초안' 문구 포함",
                    "key": key,
                    "role": role or "",
                })
                score -= 8

        if btype in {"document_title", "section_title", "header"} and _task_boundary_visible(payload):
            issues.append({
                "level": "warning",
                "code": "task_boundary_visible",
                "message": f"제목/헤더 '{key}' 에 task_id 문구 노출 — 독자용 섹션명 사용",
                "key": key,
                "role": role or "",
            })
            score -= 6

        if _is_card_type(btype) and isinstance(payload, dict):
            if _task_boundary_visible(payload):
                issues.append({
                    "level": "warning",
                    "code": "task_boundary_visible",
                    "message": f"card '{key}' 에 task_id 문구 노출",
                    "key": key,
                    "role": role or "",
                })
                score -= 6
            if _duplicate_title_heading(payload):
                issues.append({
                    "level": "info",
                    "code": "duplicate_title_heading",
                    "message": f"card '{key}' title 과 content ## 중복",
                    "key": key,
                    "role": role or "",
                })
                score -= 3
            if role in _SUMMARY_ROLES and _card_bullet_count(payload) < 3:
                issues.append({
                    "level": "info",
                    "code": "short_executive_summary",
                    "message": f"요약 '{key}' bullet 3개 미만",
                    "key": key,
                    "role": role or "",
                })
                score -= 5
            if role in _SUMMARY_ROLES and _thin_executive_text(payload):
                issues.append({
                    "level": "warning",
                    "code": "thin_executive_summary",
                    "message": f"요약 '{key}' 에 모집단 숫자·고유 사실이 없음",
                    "key": key,
                    "role": role or "",
                })
                score -= 6
            if role in {"chart_insight", "table_insight"} and _thin_insight_text(payload):
                issues.append({
                    "level": "warning",
                    "code": "thin_insight",
                    "message": (
                        f"insight '{key}' 가 빈약함 — 항목명+숫자 2~4문장 "
                        "(「데이터가 보여줍니다」 금지)"
                    ),
                    "key": key,
                    "role": role or "",
                })
                score -= 6
            content = payload.get("content")
            if isinstance(content, str) and len(_BOILERPLATE.findall(content)) > 1:
                issues.append({
                    "level": "info",
                    "code": "duplicate_boilerplate",
                    "message": f"card '{key}' QA boilerplate 중복",
                    "key": key,
                    "role": role or "",
                })
                score -= 3

    if not roles_present.intersection(_SUMMARY_ROLES):
        issues.append({
            "level": "warning",
            "code": "missing_executive_summary",
            "message": "data.role: executive_summary 또는 kpi_row 없음",
            "key": "",
            "role": "",
        })
        score -= 10

    if not any(_is_table_type(t) for t, _, _ in leaf_sequence):
        issues.append({
            "level": "warning",
            "code": "missing_table",
            "message": "table 계열 블록 없음",
            "key": "",
            "role": "",
        })
        score -= 10

    if not chart_keys:
        issues.append({
            "level": "warning",
            "code": "missing_chart",
            "message": "chart 계열 블록 없음",
            "key": "",
            "role": "",
        })
        score -= 10

    if chart_keys and "chart_insight" not in roles_present:
        issues.append({
            "level": "warning",
            "code": "missing_chart_insight",
            "message": "data.role: chart_insight 없음",
            "key": "",
            "role": "chart_insight",
        })
        score -= 8

    chart_insight_count = sum(1 for _, _, r in leaf_sequence if r == "chart_insight")
    if len(chart_keys) > chart_insight_count:
        issues.append({
            "level": "warning",
            "code": "chart_insight_count_mismatch",
            "message": (
                f"chart {len(chart_keys)}개 대비 chart_insight {chart_insight_count}개 — "
                "차트마다 직후 insight_card(chart_insight) 필요"
            ),
            "key": "",
            "role": "chart_insight",
        })
        score -= 8

    if table_keys and "table_insight" not in roles_present:
        issues.append({
            "level": "warning",
            "code": "missing_table_insight",
            "message": "data.role: table_insight 없음",
            "key": "",
            "role": "table_insight",
        })
        score -= 8

    table_insight_count = sum(1 for _, _, r in leaf_sequence if r == "table_insight")
    if len(table_keys) > table_insight_count:
        issues.append({
            "level": "warning",
            "code": "table_insight_count_mismatch",
            "message": (
                f"table {len(table_keys)}개 대비 table_insight {table_insight_count}개 — "
                "표마다 직후 insight_card(table_insight) 필요"
            ),
            "key": "",
            "role": "table_insight",
        })
        score -= 8

    if "conclusions" not in roles_present:
        issues.append({
            "level": "warning",
            "code": "missing_conclusions",
            "message": "data.role: conclusions (closing_card) 없음 — 보고서는 결론 섹션으로 종료",
            "key": "",
            "role": "conclusions",
        })
        score -= 10

    if leaf_sequence:
        last_type, last_key, last_role = leaf_sequence[-1]
        if last_role != "conclusions" and last_type != "closing_card":
            issues.append({
                "level": "warning",
                "code": "closing_not_last",
                "message": "마지막 블록이 closing_card(conclusions) 가 아님",
                "key": last_key,
                "role": last_role or "",
            })
            score -= 8

    for required in PATTERN_REQUIRED_ROLES:
        if required not in roles_present:
            issues.append({
                "level": "info",
                "code": "missing_required_role",
                "message": f"패턴 필수 role '{required}' 없음",
                "key": "",
                "role": required,
            })
            score -= 4

    # chart 직후 insight_card(chart_insight) 쌍 (순서)
    for i, (btype, key, role) in enumerate(leaf_sequence):
        if not _is_chart_type(btype):
            continue
        paired = False
        if i + 1 < len(leaf_sequence):
            ntype, _, nrole = leaf_sequence[i + 1]
            if ntype == "insight_card" and nrole == "chart_insight":
                paired = True
        if not paired:
            issues.append({
                "level": "warning",
                "code": "chart_insight_not_adjacent",
                "message": f"chart '{key}' 직후 insight_card(chart_insight) 없음",
                "key": key,
                "role": role or "",
            })
            score -= 6

    # table 직후 insight_card(table_insight) 쌍 (순서)
    for i, (btype, key, role) in enumerate(leaf_sequence):
        if not _is_table_type(btype):
            continue
        paired = False
        if i + 1 < len(leaf_sequence):
            ntype, _, nrole = leaf_sequence[i + 1]
            if ntype == "insight_card" and nrole == "table_insight":
                paired = True
        if not paired:
            issues.append({
                "level": "warning",
                "code": "table_insight_not_adjacent",
                "message": f"table '{key}' 직후 insight_card(table_insight) 없음",
                "key": key,
                "role": role or "",
            })
            score -= 6

    root_desc = doc.get("description")
    if isinstance(root_desc, str) and re.search(r"초안", root_desc):
        issues.append({
            "level": "warning",
            "code": "draft_in_description",
            "message": "루트 description 에 '초안' 문구 포함",
            "key": "",
            "role": "",
        })
        score -= 8

    score = max(0, min(100, score))
    errors = [i for i in issues if i["level"] == "error"]
    return {
        "score": score,
        "passed": len(errors) == 0 and score >= 60,
        "issues": issues,
    }
