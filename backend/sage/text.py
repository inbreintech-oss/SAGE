"""User-facing Korean — progress/SSE 는 완성형(NFC). Gemini 가 NFD 자모를 내는 경우가 많다."""

from __future__ import annotations

import unicodedata

_UNICODE_SPACES = dict.fromkeys(
    map(ord, "\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f"),
    None,
)


def nfc_user_text(message: str) -> str:
    if not message:
        return ""
    return unicodedata.normalize("NFC", str(message)).translate(_UNICODE_SPACES)
