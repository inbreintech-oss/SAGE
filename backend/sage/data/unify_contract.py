"""pangeaze unify_logic_code 정적 계약 — 0행 성공·파일 필수 오해 재발 방지."""

from __future__ import annotations

import ast
import re

_EMPTY_DF_RE = re.compile(r"pd\.DataFrame\s*\(\s*columns\s*=")
_STOCK_CODE_RE = re.compile(r"""['"](\d{6})['"]""")
_FILE_IDS_EMPTY_RE = re.compile(r"FILE_SOURCE_IDS\s*(?::\s*list\[[^\]]+\]\s*)?=\s*\[\s*\]")
_FILE_REQUIRED_MSG_RE = re.compile(
    r"종목 파일이 없습니다|파일 소스 또는 질의에 종목코드|파일에 종목코드 행이 필요"
)


def _has_except_exception(code: str) -> bool:
    """주석·docstring 의 'except Exception' 문구는 무시하고 실제 except 절만 본다."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return bool(re.search(r"except\s+(?:Exception|BaseException)\b", code))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        types: list[ast.AST] = []
        if node.type is None:
            continue
        if isinstance(node.type, ast.Tuple):
            types.extend(node.type.elts)
        else:
            types.append(node.type)
        for t in types:
            if isinstance(t, ast.Name) and t.id in ("Exception", "BaseException"):
                return True
    return False


def validate_unify_logic_code(code: str) -> None:
    """LLM unify.py 가 빈 parquet 을 성공으로 남기지 못하게 한다.

    파일 소스는 필수가 아니다. 도구만으로 질의 선정 목록을 두고 call 할 수 있다.
    금지하는 것은 0행 성공·FAIL 삼킴, 그리고 없는 파일을 필수로 요구하는 코드다.
    """
    issues: list[str] = []
    if _EMPTY_DF_RE.search(code):
        issues.append(
            "pd.DataFrame(columns=...) 금지 — 0행을 성공 return 하지 말고 "
            "raise RuntimeError (도구 FAIL 메시지를 포함)"
        )
    if _has_except_exception(code):
        issues.append(
            "unify.py 에 `except Exception`(또는 BaseException) 이 있다. "
            "reporter 용 try/except·safe_report 도 금지. "
            "수정: `except Exception` 줄을 전부 삭제하고 "
            "`if reporter: reporter.update(\"...\", state=\"running\")` 만 쓴다. "
            "`await call(...)` 은 try 없이 호출하고 실패는 그대로 raise."
        )
    uses_bridge = "InMemoryDataBridge.get" in code
    if uses_bridge and _FILE_REQUIRED_MSG_RE.search(code):
        issues.append(
            "파일 소스가 없으면 InMemoryDataBridge.get 으로 파일을 강제하지 말 것 — "
            "질의로 종목 목록을 만들고 도구만 호출한다"
        )
    tickers = set(_STOCK_CODE_RE.findall(code))
    if _FILE_IDS_EMPTY_RE.search(code) and 1 <= len(tickers) <= 15:
        issues.append(
            "도구만 통합인데 종목코드가 15개 이하이다. user_query 종목 수만큼 "
            "SELECTED_TICKERS 를 채워라. 샘플 3개·시총 상위 10개로 축소 금지"
        )
    if "raise " not in code and 'state="failed"' not in code and "state='failed'" not in code:
        issues.append(
            "0행·status!=SUCCESS 이면 raise RuntimeError 또는 "
            "reporter.update(..., state='failed') — completed 로 끝내지 말 것"
        )
    if issues:
        raise ValueError("unify_logic_code 계약 위반:\n- " + "\n- ".join(issues))
