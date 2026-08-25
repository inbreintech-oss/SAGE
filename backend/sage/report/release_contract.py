"""Release codegen contract — instruction·runtime enrich·최소 validator 동기."""

from __future__ import annotations

# ReleaseTaskValidator — pattern 과 message 1:1 (instruction.md 7번과 동일 문구)
RELEASE_FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"apply_upstream_source_updates",
        "release: apply_upstream_source_updates 금지 — "
        "apply_upstream_patches(ctx.rid, {upstream_tid: []}) 또는 "
        '[{"old": "snippet", "new": "..."}] 만 (instruction.md 7번)',
    ),
)

MSG_PATCH_REQUIRED = (
    "release: apply_upstream_patches(ctx.rid, {upstream_tid: [ops]}) 필수 — "
    "narrative 는 최소 {tid: []}. instruction.md 7번·release_api 참고"
)
MSG_SELF_PATCH_ONLY = (
    "release: apply_upstream_patches 에 release 자신(task.task_id)만 넣지 말 것 — "
    "narrative/visual 등 upstream tid"
)
MSG_HANGUL_TOFU = (
    "release: 한글 본문을 유니코드 공백(\\u2006 등)으로 치환한 코드 금지 — "
    "draft 문자열을 새로 쓰지 말고 get_result 초안을 출판할 것"
)

RELEASE_ATTACH_USAGE = (
    "llm_attach `upstream_payloads`(narrative report_document 포함)·`upstream_sources`는 **화면 QA용** — "
    "**code에 복사·embed 금지**. executor는 아래 API만 사용:\n"
    "1) draft: `draft = ctx.get_result(narrative_tid, 'report_document')` → dict 수정 → "
    "`ctx.update_task(narrative_tid, key='report_document', value=draft)`\n"
    "2) upstream: `apply_upstream_patches(ctx.rid, {upstream_tid: []})` — 변경 없으면 `[]`, "
    "문구 수정 시만 `[{'old': 'upstream_sources와 일치 snippet', 'new': '...'}]`"
)

RELEASE_CODEGEN_STEPS = (
    "release codegen 순서: (1) attach draft QA → get_result dict patch → update_task "
    "(2) finalize_report_document → update_task key=report "
    "(3) update_task key=release_summary "
    "(4) apply_upstream_patches — narrative tid는 항상 포함, ops는 snippet 수준만. "
    "한글 카드 content/title 을 새 리터럴로 재작성하지 말 것"
)


def release_executor_rules_markdown() -> str:
    """runtime_contract(release) append — instruction 선행 가이드."""
    forbidden = "\n".join(f"- {msg}" for _, msg in RELEASE_FORBIDDEN_PATTERNS)
    return f"""## Release codegen (instruction.md 7번)

{RELEASE_CODEGEN_STEPS}

### llm_attach
- {RELEASE_ATTACH_USAGE}

### 필수 API
- `apply_upstream_patches(ctx.rid, {{upstream_tid: [ops]}})` — body에 **반드시** 호출
- narrative upstream: `{{narrative_tid: []}}` — QA 없어도 re-save **필수**
- executor 문구 수정: `[{{"old": "upstream_sources 와 일치 snippet", "new": "..."}}]` 만
- 한글 본문 재작성 금지. junk·placeholder·수치 불일치만 dict 필드 patch
- 유니코드 공백으로 한글을 채우지 말 것

### 금지 API (validator)
{forbidden}
"""
