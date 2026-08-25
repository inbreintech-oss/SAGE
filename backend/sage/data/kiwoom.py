"""Kiwoom Open API helpers for market data ingestion.

Access token is read from the environment only — never hardcode credentials.
Set ``KIWOOM_ACCESS_TOKEN`` in ``.env`` (see ``.env.example``).
"""

from __future__ import annotations

import os

import requests
from tqdm import tqdm

from utils.cache import cache

# HOST = 'https://mockapi.kiwoom.com'  # 모의투자
HOST = "https://api.kiwoom.com"  # 실전투자


def _access_token() -> str:
    """Return Bearer token from env; raise if missing (never fall back to a literal)."""
    token = (os.environ.get("KIWOOM_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError(
            "KIWOOM_ACCESS_TOKEN 이 설정되지 않았습니다. "
            ".env 에 KIWOOM_ACCESS_TOKEN=... 를 넣고 프로세스/서버를 재시작하세요."
        )
    return token


def get_headers(api_id, cont_yn="N", next_key=""):
    """공통 헤더 — 매 호출 시 env 토큰을 읽어 만료 교체 후에도 재시작만으로 반영."""
    return {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {_access_token()}",
        "cont-yn": cont_yn,
        "next-key": next_key,
        "api-id": api_id,
    }


@cache
def ka10001(stk_cd):
    """개별 종목 정보 (TR ka10001)."""
    endpoint = "/api/dostk/stkinfo"
    url = HOST + endpoint

    headers = get_headers(api_id="ka10001")
    params = {"stk_cd": stk_cd}

    try:
        response = requests.post(url, headers=headers, json=params)
        return response.json()
    except Exception as e:
        print(f"ka10001 호출 에러: {e}")
        return None


@cache
def ka10099(mrkt_tp="0"):
    """종목정보 리스트 (TR ka10099). mrkt_tp: 0=코스피, 10=코스닥."""
    endpoint = "/api/dostk/stkinfo"
    url = HOST + endpoint

    headers = get_headers(api_id="ka10099")
    params = {"mrkt_tp": mrkt_tp}

    try:
        response = requests.post(url, headers=headers, json=params)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"ka10099 호출 에러: {e}")
        return None


@cache
def get_total_items():
    mrkt_tp = ["0", "10"]  # 0:코스피, 10:코스닥
    total_items = []
    for mrkt in mrkt_tp:
        res = ka10099(mrkt)
        items_mrkt = res["list"]
        total_items.extend(items_mrkt)
    return total_items


@cache
def get_items():
    """전체 목록 → 종목별 ka10001 → 재무 필드만 추려 반환."""
    total_list = get_total_items()
    fields = {
        **{
            f: f
            for f in [
                "per",
                "pbr",
                "eps",
                "roe",
                "ev",
                "bps",
                "sale_amt",
                "bus_pro",
                "cup_nga",
            ]
        }
    }
    items = []

    print(f"총 {len(total_list)}개 종목 상세 정보 수집 시작...")

    for base_item in tqdm(total_list, desc=get_items.__name__):
        code = base_item["code"]
        detail = ka10001(code)

        if detail and detail.get("return_code") == 0:
            refined_item = {
                "code": code,
                **{
                    fields[old_key]: detail.get(old_key)
                    for old_key in fields
                    if old_key in detail
                },
            }
            items.append(refined_item)

        # API 과부하 방지 — 필요 시 대기
        # time.sleep(0.1)

    return items


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv())
    res = get_items()
    print(res)
