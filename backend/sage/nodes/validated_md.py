"""validated.md hygiene — lesson 보조 기록 오염 방지."""

from __future__ import annotations

import re
from pathlib import Path

# executable / codegen 템플릿 — prompt 에 넣으면 LLM 이 복사함
_STALE_IMPORT_RE = re.compile(
    r"from\s+sage\.context\s+import|sage\.models\.report_task|def\s+process_data\s*\(",
    re.I,
)
_SYNC_RUN_TASK_RE = re.compile(r"(?<![a]sync\s)def\s+run_task\s*\(", re.I)
_JSON_TASK_OUTPUT_RE = re.compile(
    r'"task_id"\s*:|"code"\s*:\s*"(?:import|\\nimport)',
    re.I,
)
_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)

# instruction 과 모순되는 **권장** 조언 (「하지 말 것」 설명은 제외)
_FORBIDDEN_ADVICE: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"value\s*=\s*df\b", re.I), "DataFrame update_task value"),
    (re.compile(r"update_task\([^)]*value\s*=\s*\w*[Dd]f\b", re.I), "DataFrame update_task"),
    (re.compile(r"to_dict\s*\(\s*['\"]records['\"]", re.I), "raw records downstream"),
)

# 같은 줄에 있으면 anti-pattern **설명** (오염 아님)
_PROHIBITIVE_RE = re.compile(
    r"금지|제거|하지\s*말|하지\s*마|위반|잘못|오류|삭제|avoid|don't|never|remove|"
    r"제거합|넣지\s*말|사용\s*금지|전달\s*금지|호출을\s*제거",
    re.I,
)

MAX_PROMPT_CHARS = 3500
MAX_PROMPT_LINES = 45
MAX_LESSON_LINES = 15


def _line_is_prohibitive(line: str) -> bool:
    return bool(_PROHIBITIVE_RE.search(line))


def _line_forbidden_advice_label(line: str) -> str | None:
    """금지·위반 설명이 아닌, 문제 패턴을 권장하는 줄만."""
    if _line_is_prohibitive(line):
        return None
    for pat, label in _FORBIDDEN_ADVICE:
        if pat.search(line):
            return label
    return None


def _filter_forbidden_advice_lines(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        if _line_forbidden_advice_label(line):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text)


def _strip_json_task_blobs(text: str) -> str:
    """TaskOutput 형태 JSON 블록 제거."""
    lines = text.splitlines()
    out: list[str] = []
    in_json = False
    brace_depth = 0
    for line in lines:
        stripped = line.strip()
        if not in_json and stripped.startswith("{") and (
            '"task_id"' in line or '"code"' in line
        ):
            in_json = True
            brace_depth = line.count("{") - line.count("}")
            if brace_depth <= 0 and stripped.endswith("}"):
                in_json = False
            continue
        if in_json:
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                in_json = False
            continue
        if _JSON_TASK_OUTPUT_RE.search(line):
            continue
        out.append(line)
    return "\n".join(out)


def _strip_import_lines(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*(import |from )", line):
            continue
        kept.append(line)
    return "\n".join(kept)


def pollution_reasons(text: str) -> list[str]:
    """오염 패턴 — sanitize 후에도 남으면 prompt/save 거부."""
    if not text.strip():
        return []
    reasons: list[str] = []
    for line in text.splitlines():
        if _line_is_prohibitive(line):
            continue
        if _STALE_IMPORT_RE.search(line):
            reasons.append("stale import (sage.context / report_task / process_data)")
            break
        if _SYNC_RUN_TASK_RE.search(line):
            reasons.append("sync def run_task")
            break
        label = _line_forbidden_advice_label(line)
        if label:
            reasons.append(f"forbidden advice: {label}")
            break
    if _CODE_FENCE_RE.search(text):
        reasons.append("code fence block")
    if _JSON_TASK_OUTPUT_RE.search(text):
        reasons.append("TaskOutput JSON blob")
    if len(text) > MAX_PROMPT_CHARS:
        reasons.append(f"too large ({len(text)} chars)")
    if text.count("\n") > MAX_PROMPT_LINES:
        reasons.append(f"too many lines ({text.count(chr(10))})")
    return reasons


def sanitize_validated(text: str) -> str:
    """코드·JSON·import 라인 제거 후 lesson 본문만."""
    if not text.strip():
        return ""
    t = text
    t = _strip_code_fences(t)
    t = _strip_json_task_blobs(t)
    t = _strip_import_lines(t)
    t = _filter_forbidden_advice_lines(t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t


def normalize_lesson(text: str, *, error_msg: str = "") -> str:
    """저장·prompt용 lesson — 코드 없이 bullet 요약만."""
    t = sanitize_validated(text or "")
    if not t and error_msg:
        t = (
            f"### 위반 원인\n* {error_msg.strip()[:400]}\n\n"
            "### 수정 포인트\n"
            "* instruction.md·runtime_contract import·async run_task 준수"
        )
    if len(t.splitlines()) > MAX_LESSON_LINES:
        t = "\n".join(t.splitlines()[:MAX_LESSON_LINES]) + "\n...(truncated)"
    return t


def is_lesson_saveable(text: str) -> bool:
    normalized = normalize_lesson(text)
    return bool(normalized.strip()) and not pollution_reasons(normalized)


def prepare_for_prompt(text: str) -> tuple[str, list[str]]:
    """prompt 주입용 — sanitize + 잔여 오염 검사."""
    cleaned = sanitize_validated(text)
    reasons = pollution_reasons(cleaned)
    if reasons:
        return "", reasons
    return cleaned, []


_SECTION_HEADER_RE = re.compile(r"^## \[([^\]]+)\]", re.M)


def extract_category_sections(text: str, categories: frozenset[str]) -> str:
    """validated.md 에서 특정 validator 섹션만 추출."""
    if not text.strip() or not categories:
        return ""
    parts: list[str] = []
    for m in _SECTION_HEADER_RE.finditer(text):
        cat = m.group(1)
        if cat not in categories:
            continue
        start = m.start()
        nxt = _SECTION_HEADER_RE.search(text, m.end())
        end = nxt.start() if nxt else len(text)
        block = text[start:end].strip()
        cleaned, reasons = prepare_for_prompt(block)
        if cleaned and not reasons:
            parts.append(cleaned)
    return "\n---\n".join(parts)


def load_report_task_shared_lessons(
    node_dir: Path | str,
    categories: frozenset[str],
    *,
    max_siblings: int = 3,
) -> str:
    """report/task/* 형제 노드 validated.md — 공통 validator lesson 공유."""
    try:
        node_path = Path(node_dir).resolve()
        if node_path.parent.name != "task" or "report" not in node_path.parts:
            return ""
        task_root = node_path.parent
        chunks: list[str] = []
        for sibling in sorted(task_root.iterdir()):
            if not sibling.is_dir() or sibling.resolve() == node_path:
                continue
            vpath = sibling / "validated.md"
            if not vpath.is_file():
                continue
            block = extract_category_sections(
                vpath.read_text(encoding="utf-8"), categories
            )
            if block:
                chunks.append(f"### ({sibling.name} task)\n{block}")
            if len(chunks) >= max_siblings:
                break
        return "\n\n".join(chunks)
    except OSError:
        return ""


def reconcile_validated_file(text: str) -> tuple[str | None, list[str]]:
    """
    파일 reconcile — 오염 제거.
    Returns (new_content or None to delete, actions/warnings).
    """
    actions: list[str] = []
    if not text.strip():
        return "", actions

    cleaned = sanitize_validated(text)
    if cleaned != text.strip():
        actions.append("stripped code/json/import/bad-advice lines from validated.md")

    reasons = pollution_reasons(cleaned)
    if reasons:
        actions.append(f"polluted after sanitize: {'; '.join(reasons)}")
        return None, actions

    if not cleaned.strip():
        actions.append("empty after sanitize")
        return None, actions

    return cleaned, actions
