"""도구 생성 프롬프트용 SecretKey 안내 (값은 포함하지 않음)."""

from __future__ import annotations

from sage.db import saged
from sage.models import doc
from sage.secret.crypto import normalize_key_name


def format_secret_usage_block(
    secret_id: str,
    key_names: list[str],
    provider: str = "",
) -> str:
    """실제 등록 key_name 만 스니펫에 넣는다. 없는 API_TOKEN 을 만들지 말 것."""
    secret_id = (secret_id or "").strip()
    names = [normalize_key_name(k) for k in key_names if k and str(k).strip()]
    if not secret_id or not names:
        return ""

    lines = [
        "## 등록된 Secret Key (MUST)",
        f"- secret_id: `{secret_id}`",
    ]
    if provider:
        lines.append(f"- provider: `{provider}` — 코드에서는 provider 로 조회하지 말고 SECRET_ID 만 사용")
    lines.append("- key_name: " + ", ".join(f"`{n}`" for n in names))
    lines.append("")
    lines.append("```python")
    lines.append("from sage.secret import get_secret")
    lines.append("")
    lines.append(f'SECRET_ID = "{secret_id}"')
    for name in names:
        lines.append(f'{name} = await get_secret("{name}", secret_id=SECRET_ID)')
    lines.append("```")
    lines.append("`@mcp.tool` 에서 위 await 를 쓰면 **async def**. 키 값을 소스에 쓰지 말 것.")

    if (provider or "").strip().lower() == "kis":
        lines.extend(
            [
                "",
                "## kis OpenAPI 골격 (이 secret 이 붙은 도구만)",
                "기상 예시의 sync `def` 를 복사하지 말 것. 아래를 그대로 따른다.",
                "",
                "```python",
                "import httpx",
                "from sage.data.kis_auth import KIS_BASE_URL, get_kis_access_token",
                "",
                "token = await get_kis_access_token()",
                "headers = {",
                '    "content-type": "application/json; charset=utf-8",',
                '    "authorization": f"Bearer {token}",',
                '    "appkey": APP_KEY,',
                '    "appsecret": APP_SECRET,',
                '    "tr_id": TR_ID,',
                '    "custtype": "P",',
                "}",
                "async with httpx.AsyncClient(timeout=15.0) as client:",
                "    resp = await client.get(f\"{KIS_BASE_URL}{API_PATH}\", headers=headers, params=params)",
                "resp.raise_for_status()",
                "data = resp.json()",
                'if str(data.get("rt_cd")) not in ("0", "00"):',
                '    raise RuntimeError(data.get("msg1") or "vendor error")',
                "```",
                "- `TR_ID` / `API_PATH` 는 사용자 질의 상수. host 는 `KIS_BASE_URL` 만.",
                "- `params` 키는 해당 TR 공식명 (국내주식 시세/수급은 보통 "
                "`FID_COND_MRKT_DIV_CODE`, `FID_INPUT_ISCD`). 영어 `ticker`/`start_date` 금지.",
                "- 종목 기본값 `005930`. 실패는 raise — `status=\"FAIL\"` 반환 금지.",
            ]
        )
    return "\n".join(lines)


async def build_secret_prompt(
    secret_id: str | None,
    key_names: list[str] | None,
    *,
    user_id: str = "admin",
) -> str:
    if not secret_id and not key_names:
        return ""

    secret_id = (secret_id or "").strip()
    normalized = [normalize_key_name(k) for k in (key_names or []) if k and str(k).strip()]

    record = None
    if secret_id:
        record = await saged.load(doc.SecretKey, secret_id)
        if record and record.user_id != user_id:
            record = None
        if record and not normalized:
            normalized = [item.key_name for item in record.keys]

    if not secret_id or not normalized:
        return ""

    provider = (record.provider if record else "") or ""
    return format_secret_usage_block(secret_id, normalized, provider)
