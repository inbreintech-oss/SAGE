#!/usr/bin/env python3
"""progress 메시지는 NFD 자모를 NFC 완성형으로."""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sage.text import nfc_user_text


def main() -> int:
    nfd = unicodedata.normalize("NFD", "조회 정보 완료")
    out = nfc_user_text(nfd)
    if out != "조회 정보 완료":
        raise SystemExit(f"NFC failed: {out!r} from {nfd!r}")
    if nfc_user_text("정버") != "정버":
        raise SystemExit("typo must not be silently rewritten")
    print("OK progress_nfc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
