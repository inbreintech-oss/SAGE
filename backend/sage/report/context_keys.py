"""TaskContext output keys — runner·enrich·validator 공통 (플랫폼 계약).

도메인별 산출 key 는 plan task instruction·칠판 catalog 에 따름.
여기는 ``collect_report_result`` / ``llm_attach`` 와 직접 연결된 key 만 정의한다.
"""

from __future__ import annotations

# narrative → reports/{rid}/draft.json
NARRATIVE_DRAFT_KEY = "report_document"

# release → reports/{rid}/report.json (legacy alias 포함)
RELEASE_REPORT_KEYS = ("report", "layout", "report_layout")
RELEASE_REPORT_KEY = "report"
RELEASE_SUMMARY_KEY = "release_summary"

# release codegen llm_attach 필드 (TaskContext key 아님)
LLM_ATTACH_RELEASE_FIELDS = frozenset({
    "upstream_payloads",
    "upstream_sources",
})
