"""Codegen executor contract — validator 와 enrich runtime_contract 가 공유하는 단일 규칙."""

from __future__ import annotations

import re

# TaskExecutorPatternsValidator — pattern 과 message 1:1
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"from\s+sage\.context\s+import", "sage.context import 금지"),
    (r"sage\.models\.report_task", "report_task import 금지"),
    (r"\bctx\.log\b", "ctx.log 금지 — safe_report(reporter, ...) 사용"),
    (
        r"await\s+safe_report\s*\(",
        "safe_report 는 동기 함수 - await 금지, safe_report(reporter, \"...\") 만 사용",
    ),
    (r"await\s+reporter\.update\s*\(", "reporter.update() 는 동기 함수 - await 금지"),
    (r"await\s+ctx\.save\s*\(", "ctx.save() 는 동기 함수 - await 금지"),
    (r"await\s+apply_pending_updates\s*\(", "apply_pending_updates 는 동기 - await 금지"),
    (r"def\s+safe_report\s*\(", "safe_report 정의 금지 — prelude 주입 심볼 사용"),
    (r"TaskContext\.load\s*\(", "TaskContext.load() 금지 — runner 가 주입한 ctx 사용"),
    (r"\bdump_path\b", "dump_path 금지 — 저장 루트는 cfg 고정, ctx 인자만 사용"),
    (r"\bflat_storage\b", "flat_storage 제거됨 — ctx.get_result(task_id, key) 사용"),
    (
        r"to_dict\s*\(\s*orient\s*=\s*['\"]records['\"]",
        "raw row json(to_dict records) downstream 전달 금지",
    ),
    (
        r"to_dict\s*\(\s*['\"]records['\"]",
        "raw row json(to_dict records) downstream 전달 금지",
    ),
    (
        r'data_type\s*=\s*["\'](?:parquet|csv|pd\.DataFrame|DataFrame)["\']',
        "TaskContext data_type parquet/csv/DataFrame 금지 — json dict/list 만",
    ),
    (r"\.to_parquet\s*\(", "ctx.update_task 에 parquet 저장 금지 — dict/list 집계 결과만"),
    (r"\.to_csv\s*\(", "ctx.update_task 에 csv 저장 금지 — dict/list 집계 결과만"),
    (
        r"update_task\s*\([^)]*value\s*=\s*\w*[Dd]f\b",
        "DataFrame 을 update_task value 로 저장 금지 — dict/list 로 집계 후 저장",
    ),
)

PROGRESS_JARGON_RE = re.compile(
    r"PangeaSchema|StockPriceSeries|TaskContext|\bupstream\b|"
    r"plan_updates|get_result|queue_update|apply_pending_updates|"
    r"InMemoryDataBridge|PangeaExDataFrame|llm_attach|tool_path|"
    r"get_stock_|dump_tool_response|\btask-",
    re.I,
)

PROGRESS_MSG_RE = re.compile(
    r"(?:safe_report\s*\(\s*reporter\s*,|reporter\.update\s*\()\s*"
    r"f?[\"']([^\"']{4,})[\"']",
    re.I,
)

DATASET_CONTEXT_FOOTNOTE = (
    "\n---\n"
    "**[dataset_context 참고]** `samples` 는 스키마·프로파일용 3행 예시입니다. "
    "`ctx.update_task` value 로 `to_dict(records)`·samples 복사 **금지** — "
    "집계 dict/list 만 저장하세요."
)


def executor_rules_markdown() -> str:
    """runtime_contract enrich 에 append — validator FORBIDDEN_PATTERNS 와 동기."""
    forbidden = "\n".join(f"- {msg}" for _, msg in FORBIDDEN_PATTERNS)
    return f"""## Codegen executor rules (validator-synced)

### TaskContext · 저장
- runner 가 주입한 `ctx` 만 사용 — `TaskContext.load()`·경로 하드코딩 금지
- `ctx.update_task(task_id, key=..., value=<dict|list>, description=...)` — 단일 key
- `ctx.update_task(task_id, result_key=<dict|list>, ..., description=...)` — **복수 key kwargs** (visual chart/table 등)
- 위 호출 후 `ctx.save()` (**동기**, await 금지)
- `value` = 통계·ranking·summary·chart spec 등 **최소 json** (raw row·DataFrame·parquet/csv 금지)
- `ctx.get_result(task_id, key)` — upstream_context catalog·llm_attach key 만 (탐색 loop·try/except loop 금지)
- `await call(path, tool_name, {{...}})` — positional 3-tuple 권장; `call(path=, tool_name=, tool_args=)` 도 허용
- `pd.read_parquet` / storage 직접 로드 금지 (data: PangeaExDataFrame, analyze: get_result|to_pandas)
- `pd.DataFrame(columns=[...])` 빈 fallback 금지

### 금지 패턴 (codegen body)
{forbidden}

### Progress (사용자 화면)
- `safe_report(reporter, "[단계] 한글 메시지")` — **await 금지**
- 내부 model명·MCP·TaskContext·task_id·key 이름·`plan_updates` 등 **금지** ([데이터][조회][분석][차트] 등만)

### 응답 JSON
- `async def run_task(task, ctx, reporter=None)` + helper — **import 금지** (prelude: `call`, `PangeaExDataFrame`, `safe_report`, …)
"""
