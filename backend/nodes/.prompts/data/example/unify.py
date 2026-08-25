"""unify_logic_code 샘플 — 복사 후 source_id·tool_path·필드명·선정 목록을 입력에 맞게 바꾼다.

파일 소스(type=file)는 필수가 아니다.
- 파일이 있으면 FILE_SOURCE_IDS 에 입력 source_id 를 넣고 InMemoryDataBridge 에서 키를 읽는다.
- 없으면 사용자 질의에 맞게 조회 대상 코드를 SELECTED_TICKERS 로 생성하고 도구만 호출한다.
0행이거나 도구 실패면 raise — 빈 프레임을 성공으로 남기지 않는다.
report 태스크의 safe_report / except Exception 을 복사하지 말 것.
reporter 는 if reporter: reporter.update(...) 만. await call 은 try 로 감싸지 말 것.
"""
import asyncio
from typing import Dict

import pandas as pd

from sage.data.bridge import InMemoryDataBridge
from sage.data.dump_store import dump_tool_response
from sage.mcp import call

# 입력 sources 중 type=file 의 source_id. 파일 없으면 빈 리스트 — get 호출 금지.
FILE_SOURCE_IDS: list[str] = []

# 파일 없을 때: user_query 의 종목 수만큼 6자리 코드를 채운다.
# 샘플을 3개·시총 상위 10개로 복사하지 말 것. 100종이면 100개.
SELECTED_TICKERS: list[str] = []


def _as_records(res) -> list[dict]:
    if not isinstance(res, dict):
        raise RuntimeError(f"도구 응답이 dict 가 아닙니다: {type(res).__name__}")
    status = str(res.get("status") or "").upper()
    if status and status != "SUCCESS":
        raise RuntimeError(res.get("message") or f"status={status}")
    items = res.get("items")
    if isinstance(items, list):
        return [row for row in items if isinstance(row, dict)]
    if items is None:
        return [res]
    raise RuntimeError("도구 응답에 행이 없습니다")


def _codes_from_file(did: str, source_id: str) -> list[str]:
    file_df = InMemoryDataBridge.get(did, source_id)
    if len(file_df) == 0:
        raise RuntimeError(f"파일 소스 {source_id} 에 행이 없습니다.")
    rows = file_df.to_dict(orient="records") if hasattr(file_df, "to_dict") else list(file_df)
    codes: list[str] = []
    for row in rows:
        raw = row.get("ticker") or row.get("stock_code") or row.get("srtnCd") or row.get("itcode")
        if raw is None:
            continue
        code = str(raw).strip().zfill(6)
        if code and code not in codes:
            codes.append(code)
    if not codes:
        raise RuntimeError(f"파일 소스 {source_id} 에서 종목코드를 읽지 못했습니다.")
    return codes


async def unify_data(did, reporter=None) -> Dict[str, pd.DataFrame]:
    def report(message: str, state: str = "running") -> None:
        if reporter:
            reporter.update(message, state=state)

    codes: list[str] = []
    if FILE_SOURCE_IDS:
        for sid in FILE_SOURCE_IDS:
            for code in _codes_from_file(did, sid):
                if code not in codes:
                    codes.append(code)
        report(f"[시작] 파일에서 종목 {len(codes)}개 확인")
    else:
        codes = [str(c).strip().zfill(6) for c in SELECTED_TICKERS if str(c).strip()]
        report(f"[시작] 질의 선정 종목 {len(codes)}개 조회")

    if not codes:
        raise RuntimeError("조회 대상 종목이 없습니다. 파일 소스 또는 질의 선정 목록이 필요합니다.")

    sem = asyncio.Semaphore(3)
    records: list[dict] = []

    async def fetch_one(code: str) -> list[dict]:
        async with sem:
            detail = await call("kis/stock", "get_stock_item_detail", {"itcode": code})
            dump_tool_response(did, "PangeaSchema", "kis/stock", code, detail)
            rows = _as_records(detail)
            if not rows:
                raise RuntimeError(f"{code} 상세 조회 결과가 비었습니다")
            mapped = []
            for item in rows:
                mapped.append({
                    "ticker": code,
                    "company_name": item.get("name") or item.get("stock_name") or "",
                    "price": float(item.get("price") or 0),
                })
            name = mapped[0]["company_name"] or code
            report(f"[조회] {name}({code}) 종목 정보")
            return mapped

    chunks = await asyncio.gather(*[fetch_one(code) for code in codes])
    for chunk in chunks:
        records.extend(chunk)
    if not records:
        raise RuntimeError("통합 결과가 0건입니다. 도구 응답을 확인하세요.")

    df = pd.DataFrame(records)
    report(f"[완료] 종목 기본정보 {len(df)}건 통합", state="completed")
    return {"stock_master": df}
