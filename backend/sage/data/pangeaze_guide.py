"""pangeaze codegen 사전 가이드 — validator 재시도 대신 입력 소스 기준으로 작성법을 먼저 준다."""

from __future__ import annotations

from typing import Any


def _src_type(src: Any) -> str:
    if hasattr(src, "source_type"):
        return str(getattr(src, "source_type") or "")
    if isinstance(src, dict):
        return str(src.get("source_type") or src.get("type") or "")
    return ""


def _src_get(src: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(src, name):
            val = getattr(src, name)
            if val is not None:
                return val
        if isinstance(src, dict) and name in src and src[name] is not None:
            return src[name]
    return default


def _tool_names(spec: Any) -> list[str]:
    names: list[str] = []
    blocks = spec if isinstance(spec, list) else [spec]
    for block in blocks:
        if not isinstance(block, dict):
            continue
        inner = block.get("tools") if isinstance(block.get("tools"), list) else None
        rows = inner if inner else [block]
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = row.get("name") or row.get("tool_name")
            if name:
                names.append(str(name))
    return names[:8]


def build_unify_codegen_guide(sources: list[Any] | None) -> str:
    """입력 sources 로 unify.py 작성 힌트. LLM 이 샘플 [] / safe_report 를 복사하지 않게 한다."""
    sources = sources or []
    files: list[Any] = []
    tools: list[Any] = []
    for src in sources:
        kind = _src_type(src)
        if kind == "file":
            files.append(src)
        elif kind == "tool":
            tools.append(src)

    lines: list[str] = [
        "unify.py 는 아래 입력 소스를 따른다. 샘플의 FILE_SOURCE_IDS=[] / SELECTED_TICKERS=[] 를 그대로 두지 말 것.",
        "report 태스크의 `safe_report` 를 복사하지 말 것. unify 에는 `safe_report` 함수를 만들지 말 것.",
        "reporter: `if reporter: reporter.update(\"[조회] 종목 정보 (3/100)\", state=\"running\")` 만. "
        "메시지는 완성형 한글. `정보`/`완료`/`외국인`/`기관`/`통합` — `정버`/`관료`/`애국인`/`투갬` 금지. 자모 분해 금지.",
        "`except Exception` 금지 (reporter try/except 포함). `await call(...)` 은 try 없이 호출하고 실패는 그대로 올린다.",
        "0행이면 `pd.DataFrame(columns=...)` 성공 return 하지 말고 raise RuntimeError.",
    ]

    if files:
        file_ids: list[str] = []
        lines.append("")
        lines.append("### 파일 소스 — 종목 목록은 파일에서 읽는다 (하드코딩 금지)")
        for src in files:
            sid = str(_src_get(src, "source_id", "id", default="") or "")
            path = str(_src_get(src, "path", default="") or "")
            cols = _src_get(src, "columns", default=[]) or []
            col_s = ", ".join(str(c) for c in cols[:16]) if cols else "(컬럼 메타 없음)"
            if sid:
                file_ids.append(sid)
            lines.append(f"- source_id=`{sid}` path=`{path}` columns={col_s}")
            lines.append(
                f"  `FILE_SOURCE_IDS` 에 `{sid}` 를 넣고 "
                f"`InMemoryDataBridge.get(did, \"{sid}\")` 로 키를 읽는다."
            )
        ids_lit = ", ".join(f'"{i}"' for i in file_ids)
        lines.append(f"FILE_SOURCE_IDS = [{ids_lit}]")
        lines.append("SELECTED_TICKERS = []  — 파일이 있으면 시총 상위 종목을 코드에 넣지 말 것.")
    else:
        lines.append("")
        lines.append("### 파일 소스 없음 — 도구만")
        lines.append("FILE_SOURCE_IDS = []  — InMemoryDataBridge.get 호출 금지.")
        lines.append(
            "SELECTED_TICKERS 길이는 user_query 종목 수와 같다. "
            "100종이면 100개. 시총 상위 10개로 줄이지 말 것."
        )

    if tools:
        lines.append("")
        lines.append("### 도구 소스 — spec 의 tool_path·name·args 만 사용")
        for src in tools:
            sid = str(_src_get(src, "source_id", "id", default="") or "")
            path = str(_src_get(src, "tool_path", "path", default="") or "")
            names = _tool_names(_src_get(src, "tool_spec", default={}))
            name_s = ", ".join(names) if names else "(spec 의 name 사용)"
            lines.append(f"- source_id=`{sid}` tool_path=`{path}` tools={name_s}")
            lines.append(f"  `await call(\"{path}\", \"<tool_name>\", args)` 후 dump_tool_response")

    return "\n".join(lines)


def build_pangeaze_user_query(
    user_query: str,
    sources: list[Any] | None,
    *,
    unify_error: str = "",
) -> str:
    """첫 생성부터 소스 가이드를 붙인다. 실행 실패 시에만 에러 tail 추가."""
    parts = [
        (user_query or "").strip(),
        "",
        "## unify.py 작성 가이드 (입력 소스 — 생성 전 최우선)",
        build_unify_codegen_guide(sources),
    ]
    if unify_error:
        tail = unify_error[-4000:] if len(unify_error) > 4000 else unify_error
        parts.extend(
            [
                "",
                "## unify_data 실행 오류 — schema/adapter/unify 전체 재생성",
                "위 가이드를 지키면서 이 오류만 고친다.",
                "```",
                tail,
                "```",
            ]
        )
    return "\n".join(parts)
