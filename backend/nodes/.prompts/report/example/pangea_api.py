"""data 태스크 codegen API — 호출 원형·인자·순서 (실행 코드 아님, LLM 참고용).

model 이름: enrich `dataset_context` [PANGEA TARGETS] 의 targets[].model 만 (추측·하드코딩 금지).
동기/비동기: 아래 **await** 표기 없는 함수는 await 하지 말 것.
"""

# ---------------------------------------------------------------------------
# PangeaExDataFrame — 통합 원본 (did 스키마 parquet)
# ---------------------------------------------------------------------------
#
#   from sage.data.pangea import PangeaExDataFrame
#   from sage.report.runner import safe_report
#   pgdf = PangeaExDataFrame(did=task.data_id)
#   df = pgdf.to_pandas("PangeaSchema")   # model 은 [PANGEA TARGETS] 확인
#
# ---------------------------------------------------------------------------
# plan_updates — 반환 형식 (필수 숙지)
# ---------------------------------------------------------------------------
#
#   plan = pgdf.plan_updates(model: str, keys=None, fields=None) -> list[dict]
#
#   · keys 인자: **검사할 행 식별자만** (전체 parquet X). **생략 금지** — 0행 parquet 에서
#     keys 없으면 빈 plan 이 「이미 최신」으로 오인되어 MCP 가 건너뛰어짐.
#     - 단일 키 model (keys=["ticker"]): ["005930", "000660", ...]  str list
#     - 복합 키 model (keys=["ticker","date"]): [(ticker, date), ...] tuple list
#       (ticker 만 넘겨도 됨 — dump 가 종목 단위)
#
#   · 반환 (비어 있으면 MCP 생략 — parquet 에 행이 있고 dump SUCCESS 가 TTL 내일 때만):
#     [
#       {"keys": ["005930", "000660"], "fields": ["price", "per", "market_cap"]},
#       {"keys": [("005930", "2025-01-02")], "fields": ["close_price", "volume"]},
#     ]
#
#   **item["keys"] 는 list — dict 아님. item["keys"].get(...) 금지.**
#   **item["fields"] 는 갱신 필요 컬럼명 list (str).**
#
# ---------------------------------------------------------------------------
# MCP 갱신 — 단일 키 model (예: PangeaSchema, keys=["ticker"])
# ---------------------------------------------------------------------------
#
#   plan = pgdf.plan_updates("PangeaSchema", keys=selected_tickers)
#   if not plan:
#       safe_report(reporter, "[데이터] 종목 기본 정보 최신 — 추가 조회 생략")
#   else:
#       for item in plan:
#           expired_fields = item["fields"]          # list[str]
#           for ticker in item["keys"]:              # list[str] — 한 item 에 여러 ticker 가능
#               detail = await call("kis/stock", "get_stock_item_detail", {"itcode": ticker})
#               record = {
#                   "ticker": ticker,
#                   "company_name": detail.get("name", ""),
#                   "price": float(detail.get("price", 0)),
#                   # ... schema fields 전부 (metadata targets[].fields)
#               }
#               pgdf.queue_update("PangeaSchema", [record], tool_path="kis/stock")
#       pgdf.apply_pending_updates("PangeaSchema")
#
# ---------------------------------------------------------------------------
# MCP 갱신 — 복합 키 model (예: StockPriceSeries, keys=["ticker","date"])
# ---------------------------------------------------------------------------
#
#   plan = pgdf.plan_updates("StockPriceSeries", keys=selected_tickers)
#   if not plan:
#       safe_report(reporter, "[데이터] 일별 시세 최신 — 추가 조회 생략")
#   else:
#       tickers = []
#       for item in plan:
#           for k in item["keys"]:
#               if isinstance(k, (tuple, list)):
#                   tickers.append(k[0])              # (ticker, date) → ticker
#               else:
#                   tickers.append(k)
#       for ticker in dict.fromkeys(tickers):
#           prices_res = await call("kis/stock", "get_stock_prices", {"itcode": ticker})
#           records = [
#               {"ticker": ticker, "date": p["date"], "close_price": float(p["close"]), ...}
#               for p in prices_res.get("result", [])
#           ]
#           if records:
#               pgdf.queue_update("StockPriceSeries", records, tool_path="kis/stock")
#       pgdf.apply_pending_updates("StockPriceSeries")
#
# ---------------------------------------------------------------------------
# 금지 패턴
# ---------------------------------------------------------------------------
#
#   t = item["keys"].get("ticker")          # AttributeError — keys 는 list
#   for ticker in selected_tickers: call()  # plan_updates 없이 전체 일괄 호출
#   queue_update(...) without call()         # 하드코딩 payload
#   df.to_dict(orient="records")             # ctx.update_task value 로 raw row 전달 금지
#   ctx.update_task(..., value=df)           # DataFrame 저장 금지
#
# ---------------------------------------------------------------------------
# queue_update / apply_pending_updates
# ---------------------------------------------------------------------------
#
#   pgdf.queue_update(model, [record, ...], tool_path="kis/stock")
#   pgdf.apply_pending_updates(model)          # model 마다 MCP loop 끝난 뒤 1회
#   # record 필드 타입 = dataset_context schema (int 날짜→YYYYMMDD, date→'YYYY-MM-DD')
#   # parse_date/datetime 변환 금지 — API 반환값 그대로
#   # dump/{model}/{tool_slug}/{key_slug}/data.json — report queue_update 용 (legacy flat 포함)
#
# ---------------------------------------------------------------------------
# unify (최초 구축) — dump_tool_response. 0행·FAIL 은 raise (빈 parquet 성공 금지)
# ---------------------------------------------------------------------------
#
#   from sage.data.dump_store import dump_tool_response
#   detail = await call("kis/stock", "get_stock_item_detail", {"itcode": ticker})
#   dump_tool_response(did, "PangeaSchema", "kis/stock", ticker, detail)
#   if str(detail.get("status") or "").upper() != "SUCCESS":
#       raise RuntimeError(detail.get("message") or "종목 조회 실패")
#   # 매핑·DataFrame 구성은 unify 내부 — return 후 handle_pangeaze 가 parquet 저장
#   # 전체 샘플: nodes/.prompts/data/example/unify.py
#
# ---------------------------------------------------------------------------
# MCP call (prelude 주입 — import 작성 금지)
# ---------------------------------------------------------------------------
#
#   row = await call("kis/stock", "get_stock_item_detail", {"itcode": "005930"})
#
# ---------------------------------------------------------------------------
# TaskContext — instruction.md §3 · runtime_contract (validator-synced)
# ---------------------------------------------------------------------------
#
#   ctx.update_task(task.task_id, key="<plan key>", value={"tickers": [...], "count": N}, ...)
#   ctx.save()
#   safe_report(reporter, "[조회] ...")  # 동기, await 금지
