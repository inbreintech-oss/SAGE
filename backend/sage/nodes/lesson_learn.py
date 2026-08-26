"""NodeV validated.md 학습 — contract 기반 범용 (오류 유형별 패치 없음)."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import Literal

LessonPhase = Literal["codegen", "execute", "post_validate", "runtime"]

_CONTRACT_REF = {
    "SchemaContract": "dataset_context schema.py [SCHEMA DATA TYPES]",
    "SchemaContractValidator": "dataset_context schema.py [SCHEMA DATA TYPES]",
    "ImportPath": "runtime_contract example/run_task.py import",
    "LlmImportForbiddenValidator": "runtime_contract — import 금지, run_task body 만",
    "JsonLiteralInPythonValidator": "runtime_contract — JSON true/false/null → True/False/None",
    "ReleaseTaskValidator": "release/instruction.md 7번·release_contract",
    "McpCall": "tools spec input.properties",
    "McpCallValidator": "tools spec input.properties",
    "UpstreamBoard": "upstream_context catalog·llm_attach payloads",
    "UpstreamBoardValidator": "upstream_context catalog·llm_attach payloads",
    "DataTaskFlow": "runtime_contract data 흐름 (plan_updates→call→queue_update→apply)",
    "DataTaskFlowValidator": "runtime_contract data 흐름",
    "RunTaskStructure": "runtime_contract async run_task 시그니처",
    "RunTaskStructureValidator": "runtime_contract async run_task 시그니처",
    "TaskExecutorPatterns": "instruction.md·reporter_progress",
    "TaskExecutorPatternsValidator": "runtime_contract codegen_contract (validator-synced)",
    "ToolAccessValidator": "call() 첫 인자 = 요청 tools[] / spec tool_path. tm-* generate id 금지",
}


@dataclass
class LessonEvent:
    category: str
    error_msg: str
    phase: LessonPhase = "codegen"
    attempt: int = 1


@dataclass
class LessonAccumulator:
    events: list[LessonEvent] = field(default_factory=list)

    def add(self, category: str, error_msg: str, *, phase: LessonPhase = "codegen", attempt: int = 1) -> None:
        raw = (error_msg or "").strip()
        msg = compress_error_for_lesson(raw) or raw
        if not msg:
            return
        self.events.append(
            LessonEvent(
                category=category[:80],
                error_msg=msg[:600],
                phase=phase,
                attempt=attempt,
            )
        )

    def has_events(self) -> bool:
        return bool(self.events)

    def categories(self) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for ev in self.events:
            if ev.category not in seen:
                seen.add(ev.category)
                out.append(ev.category)
        return out


def error_signature(error_msg: str) -> str:
    """유사 오류 dedupe — traceback 줄 번호·경로 제거."""
    core = compress_error_for_lesson(error_msg)
    lines = []
    for line in core.splitlines():
        s = line.strip()
        if not s:
            continue
        s = re.sub(r'File "[^"]+"', "File ...", s)
        s = re.sub(r"line \d+", "line N", s)
        lines.append(s)
    blob = "\n".join(lines[:8]) or core[:200]
    return hashlib.sha256(blob.encode("utf-8", errors="replace")).hexdigest()[:16]


_CAUSE_KEEP = 1200


def _strip_pydantic_noise(text: str) -> str:
    """ValidationError 의 [type=…, input_value=소스전체] 꼬리를 제거."""
    text = re.sub(r"\[type=.*", "", text, flags=re.S)
    text = re.sub(r"For further information visit \S+", "", text)
    return text.strip()


def compress_error_for_lesson(error_msg: str) -> str:
    """traceback → contract·exception 핵심만 (validated·retry 피드백용)."""
    text = _strip_pydantic_noise((error_msg or "").strip())
    if not text:
        return ""

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    idx = next(
        (
            i
            for i, ln in enumerate(lines)
            if "schema contract" in ln.lower() or "contract 위반" in ln or "계약 위반" in ln
        ),
        None,
    )
    if idx is not None:
        block = [lines[idx]]
        for ln in lines[idx + 1 :]:
            if ln.startswith("- ") or ln.startswith("•") or ln.startswith("- record["):
                block.append(ln)
            else:
                break
        return "\n".join(block[:12])[:_CAUSE_KEEP]

    for ln in lines:
        if "Validator" in ln or "위반" in ln:
            return ln[:_CAUSE_KEEP]

    for ln in reversed(lines):
        if re.match(r"^[\w]+Error:", ln) or re.match(r"^[\w]+Exception:", ln):
            return ln[:_CAUSE_KEEP]

    for ln in reversed(lines):
        if ln.startswith("File ") or ln.startswith("^") or "Traceback" in ln:
            continue
        if "runner.py" in ln and "line" in ln:
            continue
        if len(ln) > 15:
            return ln[:_CAUSE_KEEP]

    return text[:220].replace("\n", " | ")


def infer_lesson_category(error_msg: str) -> str:
    """validator·exception 이름 또는 contract 위반 → 섹션 키 (범용)."""
    blob = error_msg or ""
    m = re.search(r"\[(\w+Validator)\]", blob)
    if m:
        return m.group(1)
    m = re.search(r"(\w+Validator)\s*위반", blob)
    if m:
        return m.group(1)
    if "schema contract" in blob.lower() or "SchemaContractError" in blob:
        return "SchemaContract"
    m = re.search(r"^(\w+Error):", blob, re.M)
    if m:
        return m.group(1)
    return "ContractViolation"


def _contract_ref(category: str, error_msg: str) -> str:
    if category in _CONTRACT_REF:
        return _CONTRACT_REF[category]
    if "schema contract" in error_msg.lower():
        return _CONTRACT_REF["SchemaContract"]
    if "Validator" in category:
        return "instruction.md + runtime_contract + validator 메시지"
    return "instruction.md + runtime_contract"


def format_structured_lesson(
    category: str,
    error_msg: str,
    *,
    phase: LessonPhase = "codegen",
    resolved: bool = True,
) -> str:
    """validated.md 초안 — LLM reconcile 전 단계."""
    core = compress_error_for_lesson(error_msg)
    status = "재시도 후 통과 — 동일 위반 재발 금지" if resolved else "반복 주의"
    ref = _contract_ref(category, core or error_msg)
    relapse = _relapse_prevention(category, core or error_msg)
    return "\n".join(
        [
            f"### [{category}] ({phase}) {status}",
            f"* **원인**: {core or error_msg.strip()[:_CAUSE_KEEP]}",
            f"* **준수 계약**: {ref}",
            f"* **재발 방지**: {relapse}",
        ]
    )


def validated_llm_reconcile_enabled() -> bool:
    # 기본 off — LLM 이 원인·재발 방지를 일반 문구로 덮어쓰지 않게.
    v = os.environ.get("SAGE_VALIDATED_LLM_RECONCILE", "0").strip().lower()
    return v in ("1", "true", "yes")


async def llm_reconcile_validated_md(
    *,
    instruction: str,
    draft_validated: str,
    category: str,
    error_msg: str,
    resolved: bool = False,
) -> str | None:
    """instruction.md + validator 오류와 함께 validated.md 전체를 LLM 이 정리."""
    if not validated_llm_reconcile_enabled():
        return None
    from sage.llm import LLMFactory
    from sage.llm.llms import Message
    from sage.nodes.validated_md import pollution_reasons, sanitize_validated

    core = compress_error_for_lesson(error_msg)
    ref = _contract_ref(category, core or error_msg)
    prompt = (
        "당신은 NodeV validated.md 편집기입니다.\n\n"
        "## 절대 규칙\n"
        "1. **instruction.md 가 최우선** — instruction 과 모순·중복되는 validated 조언은 제거·병합\n"
        "2. bullet 요약만 — code fence, import, run_task/json task blob 금지\n"
        "3. 섹션: `## [Category]` + `- **최근 업데이트**:` + lesson bullets + `---`\n"
        "4. 같은 Category 중복 섹션은 하나로 합침 — 재발 방지 bullet 1~2개만 유지\n"
        f"5. validator: `{category}` — "
        f"{'통과 후 재발 방지' if resolved else '미해결 주의'}\n"
        f"6. 원인: {core or error_msg.strip()[:_CAUSE_KEEP]}\n"
        f"7. 준수 계약: {ref}\n\n"
        "## instruction.md (최우선)\n"
        f"{(instruction or '')[:14000]}\n\n"
        "## validated.md 초안 (instruction 에 맞게 수정해 **전체** 출력)\n"
        f"{draft_validated[:10000]}\n\n"
        "---\n"
        "출력: 수정된 validated.md 전체 markdown 만. 설명 문장·코드펜스 없음."
    )
    try:
        processor = LLMFactory.get_llm()
        raw = await processor.generate_async([Message(role="user", content=prompt)])
        text = sanitize_validated(str(raw or "").strip())
        if not text or pollution_reasons(text):
            return None
        return text
    except Exception:
        return None


def format_record_only_feedback(category: str, error_msg: str) -> str:
    """validated.md 기록 후 runner 가 같은 generate 에서 재생성."""
    core = compress_error_for_lesson(error_msg)
    ref = _contract_ref(category, core or error_msg)
    return (
        f"[{category}]\n"
        f"원인: {(core or error_msg.strip())[:_CAUSE_KEEP]}\n\n"
        f"준수 계약: {ref}\n"
        f"validated.md 에 기록됨 — 같은 요청에서 소스를 재생성한다."
    )


def _parse_board_key_error(error_msg: str) -> tuple[str | None, list[str]]:
    text = error_msg or ""
    bad_m = re.search(r"get_result key '([^']+)'", text)
    allow_m = re.search(r"허용 key:\s*(\[[^\]]+\])", text)
    bad = bad_m.group(1) if bad_m else None
    allowed: list[str] = []
    if allow_m:
        allowed = re.findall(r"'([^']+)'", allow_m.group(1))
    return bad, allowed


def _parse_tool_access_error(error_msg: str) -> tuple[str | None, list[str]]:
    """ToolAccessValidator — 허용되지 않은 도구 'x' … 목록은 ['a', 'b']."""
    text = error_msg or ""
    bad_m = re.search(r"허용되지 않은 도구 '([^']+)'", text)
    allow_m = re.search(r"사용 가능한 도구 목록은\s*(\[[^\]]+\])", text)
    bad = bad_m.group(1) if bad_m else None
    allowed: list[str] = []
    if allow_m:
        allowed = re.findall(r"'([^']+)'", allow_m.group(1))
        if not allowed:
            allowed = re.findall(r'"([^"]+)"', allow_m.group(1))
    return bad, allowed


def _relapse_prevention(category: str, error_msg: str) -> str:
    """validated.md 재발 방지 — 구체 구문. '다시 위반하지 말 것' 만으로 끝내지 않는다."""
    hint = _validator_fix_hint(error_msg)
    if hint:
        return hint.replace("\n", " ")
    if "ToolAccess" in category:
        return (
            "await call() 첫 인자는 이번 요청 tools[] / spec tool_path 만. "
            "generate 초안 tm-* tool_id 는 허용 목록에 없으면 금지."
        )
    return (
        "instruction.md·runtime_contract 와 모순 없이, "
        "위 원인 contract 를 다시 위반하지 말 것 (코드·import 템플릿 기록 금지)"
    )


def _validator_fix_hint(error_msg: str) -> str:
    """재시도 때 '반복 금지'가 아니라 이번 응답에서 지울 구문·대체 코드를 준다."""
    text = error_msg or ""
    hints: list[str] = []
    if re.search(r"except\s+(?:Exception|BaseException)", text) or "except Exception" in text:
        hints.append(
            "이번 코드에서 `except Exception` / `except BaseException` / `safe_report` 를 "
            "검색해 **0건**이 되게 하라. reporter 는 "
            '`if reporter: reporter.update("...", state="running")` 만. '
            "`await call(...)` 은 try 로 감싸지 말 것."
        )
    if "to_dict" in text and "records" in text:
        hints.append(
            "`to_dict(orient='records')` / `to_dict('records')` 를 지운다. "
            "ctx.update_task value 는 집계 dict/list 만."
        )
    if "finalize_report_document" in text and "plan_id=task.plan_id" in text:
        hints.append(
            "finalize_report_document(..., plan_id=task.plan_id, did=task.data_id, rid=ctx.rid) 를 그대로 쓴다."
        )
        hints.append(
            "파일이 있으면 FILE_SOURCE_IDS 에 입력 source_id 를 넣고 SELECTED_TICKERS 는 []. "
            "파일이 없으면 user_query 종목 수만큼 SELECTED_TICKERS 를 채운다. 시총 상위 10개 금지."
        )
    if "DataFrame(columns" in text:
        hints.append("`pd.DataFrame(columns=...)` 를 지운다. 0행이면 raise RuntimeError.")
    bad, allowed = _parse_board_key_error(text)
    if bad and allowed:
        hints.append(
            f"코드에서 {bad!r} 를 전부 제거하고 catalog key 만 그대로 사용하라 "
            f"(plan 제목·description 에서 key 이름을 만들지 말 것). "
            f"허용 key: {', '.join(allowed)}"
        )
    elif bad:
        hints.append(f"get_result key {bad!r} 를 제거하고 catalog 의 허용 key 만 사용하라.")
    tool_bad, tool_allowed = _parse_tool_access_error(text)
    if tool_bad or tool_allowed:
        if tool_allowed:
            hints.append(
                f"await call() 첫 인자를 {tool_allowed} 중 하나로 바꿔라. "
                f"{tool_bad!r} 삭제. generate 초안 tm-* id 는 허용 목록에 없으면 금지."
            )
        elif tool_bad:
            hints.append(
                f"await call() 첫 인자 {tool_bad!r} 를 지우고 "
                "이번 요청 tools[] / spec tool_path 만 사용하라."
            )
    return "\n".join(hints)


def _board_key_retry_hint(error_msg: str) -> str:
    hint = _validator_fix_hint(error_msg)
    if not hint:
        return ""
    return f"\n\n수정: {hint}"


def format_validator_system_priority_block(
    category: str,
    error_msg: str,
    *,
    attempt: int = 0,
) -> str:
    """재시도 system 최상단 — validator 오류를 instruction 앞에 (선가이드 강조)."""
    core = (compress_error_for_lesson(error_msg) or error_msg).strip()
    ref = _contract_ref(category, core or error_msg)
    bad, allowed = _parse_board_key_error(core)
    fix = _validator_fix_hint(error_msg) or _validator_fix_hint(core)
    lines = [
        "## ⚠ codegen 수정 (validator — system 최우선)",
        "이번 응답은 **출력 JSON 전체(code 포함)** 를 validator 통과하도록 **처음부터** 다시 작성.",
        f"validator: {category}",
        f"원인: {core[:_CAUSE_KEEP]}",
        f"준수 계약 (우선순위): instruction.md > runtime_contract > validated 보조 — {ref}",
        "수정: 아래 금지 구문을 제거한 코드만 제출. 설명만 바꾸고 구문을 남기면 같은 validator 에 또 실패한다.",
    ]
    if attempt >= 1:
        lines.append(
            f"직전 codegen 이 **같은 원인**으로 실패했다 (재시도 {attempt}). "
            "금지 구문 검색 결과가 0건인 코드만 받는다."
        )
    if fix:
        lines.append(fix)
    if bad:
        lines.append(f"get_result key {bad!r} 금지.")
    if allowed:
        lines.append(f"허용 key만: {', '.join(allowed)}")
    if bad:
        lines.append("(plan 제목·description 에서 key 이름을 만들지 말 것)")
    lines.append("")
    return "\n".join(lines) + "\n\n"


def format_validator_retry_user_block(
    category: str,
    error_msg: str,
    *,
    attempt: int = 0,
) -> str:
    """재시도 user message tail — validator 수정 요청 (telemetry·LLM 동일)."""
    return format_retry_feedback(category, error_msg, attempt=attempt)


def format_retry_feedback(category: str, error_msg: str, *, attempt: int = 0) -> str:
    """재시도 user message — 원인 + 이번 응답에서 지울 구문."""
    core = compress_error_for_lesson(error_msg)
    ref = _contract_ref(category, core or error_msg)
    extra = _board_key_retry_hint(error_msg)
    repeat = ""
    if attempt >= 1:
        repeat = (
            f"직전 응답이 같은 validator 에 실패했다 (codegen 재시도 {attempt}). "
            "금지 구문을 남긴 채 다시 제출하지 말 것.\n"
        )
    return (
        f"[{category}]\n"
        f"{repeat}"
        f"원인: {(core or error_msg.strip())[:_CAUSE_KEEP]}\n\n"
        f"준수 계약: {ref}\n"
        f"이번 응답에서 원인을 제거한 전체 코드를 제출하라.{extra}"
    )


def lessons_prompt_block(validated_text: str, *, max_chars: int = 2500) -> str:
    """재시도 instruction 에 주입할 validated 요약."""
    from sage.nodes.validated_md import prepare_for_prompt

    lessons, _ = prepare_for_prompt(validated_text or "")
    if not lessons:
        return ""
    return (
        "\n\n## validated 학습 (동일 contract 위반 금지)\n"
        f"{lessons[:max_chars]}\n"
    )


def consolidate_events(events: list[LessonEvent]) -> list[tuple[str, str, LessonPhase]]:
    """category 별 최신 이벤트만."""
    latest: dict[str, LessonEvent] = {}
    for ev in events:
        latest[ev.category] = ev
    return [(c, ev.error_msg, ev.phase) for c, ev in latest.items()]
