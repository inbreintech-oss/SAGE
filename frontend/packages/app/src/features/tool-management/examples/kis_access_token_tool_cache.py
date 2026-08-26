"""
한국투자증권(KIS) 접근 토큰 발급 MCP 도구 — 예제 code (도구 생성 입력용)

- SAGE 도구 생성 화면 「도구 저장용 예시 코드」에 붙여넣어 사용
- KIS 공식 가이드(토큰 파일 캐시·만료 확인·필요 시에만 tokenP 호출) 패턴 반영
- Secret: get_secret_map(SECRET_ID) — dump 시 {{SAGE_INJECT_SECRET_ID}} 가 실제 secret_id 로 치환됨

등록 가이드 (생성 폼):
  - tags/키워드: token, 토큰, 인증
  - Provider: KIS SecretKey(secret_id) 선택
  - 다른 KIS API 도구 생성 시 「연계기관 인증 토큰 도구」로 본 도구 tool_id 선택
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from sage.secret import get_secret_map

mcp = FastMCP("KoreaInvestmentToken")

# SECRET_ID 는 dump 시 서버가 주입 — placeholder 를 그대로 사용
SECRET_ID = "{{SAGE_INJECT_SECRET_ID}}"

# 모의투자(vps) — 실전(prod)은 https://openapi.koreainvestment.com:9443
KIS_BASE_URL = "https://openapivts.koreainvestment.com:29443"
KIS_TOKEN_PATH = "/oauth2/tokenP"

# 도구 디렉터리 하위 캐시 (KIS 가이드: 발급 토큰·만료시각 로컬 보관)
CACHE_DIR = Path(__file__).resolve().parent / ".kis_token_cache"


class TokenRequest(BaseModel):
    force_refresh: bool = Field(
        default=False,
        description="True 이면 캐시를 무시하고 tokenP 재발급 (기본 False — 유효 캐시 재사용)",
    )


class TokenResponse(BaseModel):
    success: bool = Field(..., description="토큰 조회/발급 성공 여부")
    access_token: Optional[str] = Field(None, description="접근 토큰")
    token_type: Optional[str] = Field(None, description="토큰 타입 (예: Bearer)")
    expires_in: Optional[int] = Field(None, description="유효 기간(초) — 신규 발급 시")
    valid_until: Optional[str] = Field(None, description="만료 일시 (YYYY-MM-DD HH:MM:SS)")
    from_cache: bool = Field(default=False, description="캐시에서 반환되었는지 여부")
    error: Optional[str] = Field(None, description="오류 메시지")


def _cache_path_for_app_key(app_key: str) -> Path:
    """동일 app_key 는 동일 캐시 파일 사용 (연속 발급 제한 완화)."""
    digest = hashlib.sha256(app_key.encode("utf-8")).hexdigest()[:24]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"kis_token_{digest}.json"


def _parse_valid_until(res_data: dict) -> Optional[datetime]:
    """
    KIS tokenP 응답에서 만료 시각 추출.
    - access_token_token_expired (KIS 가이드 필드) 우선
    - 없으면 expires_in 초로 계산
    """
    expired_raw = res_data.get("access_token_token_expired")
    if expired_raw:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(str(expired_raw).strip(), fmt)
            except ValueError:
                continue

    expires_in = res_data.get("expires_in")
    if expires_in is not None:
        try:
            return datetime.now() + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            pass
    return None


def _read_cached_token(cache_file: Path) -> Optional[dict]:
    """KIS 가이드 read_token — 만료 전이면 캐시 반환."""
    if not cache_file.is_file():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        valid_until_raw = data.get("valid_until")
        token = data.get("access_token")
        if not token or not valid_until_raw:
            return None

        valid_until = datetime.strptime(valid_until_raw, "%Y-%m-%d %H:%M:%S")
        if valid_until > datetime.now():
            return data
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return None


def _save_cached_token(
    cache_file: Path,
    *,
    access_token: str,
    token_type: Optional[str],
    valid_until: datetime,
    expires_in: Optional[int],
) -> None:
    """KIS 가이드 save_token — token + valid-date 저장."""
    payload = {
        "access_token": access_token,
        "token_type": token_type,
        "valid_until": valid_until.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_in": expires_in,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _issue_token_from_kis(app_key: str, app_secret: str) -> tuple[dict, Optional[str]]:
    url = f"{KIS_BASE_URL}{KIS_TOKEN_PATH}"
    headers = {"content-type": "application/json; charset=UTF-8"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }

    response = requests.post(url, headers=headers, json=body, timeout=10)
    response.raise_for_status()
    return response.json(), None


@mcp.tool(name="get_access_token")
def get_access_token(request: TokenRequest) -> TokenResponse:
    """
    한국투자증권 OpenAPI 접근 토큰을 반환합니다.

    - 유효한 로컬 캐시가 있으면 tokenP 를 호출하지 않습니다 (KIS 연속 발급 제한 대응).
    - force_refresh=True 일 때만 강제 재발급합니다.
    - 다른 KIS API MCP 도구는 본 도구를 연계(tools[])하여 access_token 을 받아 사용하세요.
    """
    try:
        keys = get_secret_map(SECRET_ID)
        app_key = keys.get("APPKEY")
        app_secret = keys.get("APPSECRET")

        if not app_key or not app_secret:
            return TokenResponse(
                success=False,
                error="SecretKey 에 APPKEY / APPSECRET 이 등록되어 있지 않습니다.",
            )

        cache_file = _cache_path_for_app_key(app_key)

        if not request.force_refresh:
            cached = _read_cached_token(cache_file)
            if cached:
                return TokenResponse(
                    success=True,
                    access_token=cached.get("access_token"),
                    token_type=cached.get("token_type"),
                    expires_in=cached.get("expires_in"),
                    valid_until=cached.get("valid_until"),
                    from_cache=True,
                    error=None,
                )

        res_data, _ = _issue_token_from_kis(app_key, app_secret)
        access_token = res_data.get("access_token")
        if not access_token:
            return TokenResponse(
                success=False,
                error=f"tokenP 응답에 access_token 이 없습니다: {res_data}",
            )

        valid_until = _parse_valid_until(res_data)
        if valid_until is None:
            # 만료 정보 없을 때 보수적으로 23시간 캐시 (KIS 1일 유효 가정)
            valid_until = datetime.now() + timedelta(hours=23)

        expires_in_val = res_data.get("expires_in")
        if expires_in_val is not None:
            try:
                expires_in_val = int(expires_in_val)
            except (TypeError, ValueError):
                expires_in_val = None

        _save_cached_token(
            cache_file,
            access_token=access_token,
            token_type=res_data.get("token_type"),
            valid_until=valid_until,
            expires_in=expires_in_val,
        )

        return TokenResponse(
            success=True,
            access_token=access_token,
            token_type=res_data.get("token_type"),
            expires_in=expires_in_val,
            valid_until=valid_until.strftime("%Y-%m-%d %H:%M:%S"),
            from_cache=False,
            error=None,
        )

    except requests.HTTPError as e:
        detail = ""
        if e.response is not None:
            try:
                detail = e.response.text[:500]
            except Exception:
                detail = str(e)
        return TokenResponse(success=False, error=f"tokenP HTTP 오류: {detail or e}")
    except Exception as e:
        return TokenResponse(success=False, error=f"토큰 발급 실패: {e}")


if __name__ == "__main__":
    mcp.run(log_level="ERROR", show_banner=False)
