#!/usr/bin/env python3
"""tool/generate 질의 리터럴·secret 스니펫 계약."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.secret.keys import provider_from_query
from sage.secret.prompt import format_secret_usage_block
from sage.tool.generate_guide import build_tool_codegen_guide, extract_query_literals
from sage.tool.runtime import _raise_if_tool_reported_fail


QUERY = """provider: kis
TR_ID: FHKST01010900
URL 경로: /uapi/domestic-stock/v1/quotations/inquire-investor
사용자 쿼리:
한달간 일단위 기관 외국인 수급 도구
"""


def test_literals() -> None:
    lit = extract_query_literals(QUERY)
    assert lit["tr_id"] == "FHKST01010900", lit
    assert lit["url_path"] == "/uapi/domestic-stock/v1/quotations/inquire-investor", lit
    assert provider_from_query(QUERY) == "kis"
    guide = build_tool_codegen_guide(QUERY)
    assert 'TR_ID = "FHKST01010900"' in guide
    assert 'API_PATH = "/uapi/domestic-stock/v1/quotations/inquire-investor"' in guide
    assert "get_kis_access_token" not in guide


def test_secret_snippet_uses_real_keys_only() -> None:
    block = format_secret_usage_block(
        "sk-test",
        ["APP_KEY", "APP_SECRET"],
        provider="kis",
    )
    assert "APP_KEY" in block and "APP_SECRET" in block
    assert "API_TOKEN" not in block
    assert "SECRET_ID" in block
    assert "get_kis_access_token" not in block
    assert "FID_INPUT_ISCD" not in block


def test_smoke_treats_fail_dict_as_error() -> None:
    try:
        _raise_if_tool_reported_fail({"status": "FAIL", "message": "no token"})
    except RuntimeError as e:
        assert "no token" in str(e)
    else:
        raise AssertionError("FAIL dict must raise")
    _raise_if_tool_reported_fail({"status": "SUCCESS", "items": []})


def main() -> int:
    test_literals()
    test_secret_snippet_uses_real_keys_only()
    test_smoke_treats_fail_dict_as_error()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
