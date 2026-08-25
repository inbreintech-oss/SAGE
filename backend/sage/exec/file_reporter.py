"""Progress reporter — worker 가 호스트 파일에 NDJSON append (SSE 폴링용)."""

from __future__ import annotations

import json
from pathlib import Path

from sage.logg import error, info


class FileReporter:
    """TaskReporter 호환 — bind mount 경로에 progress 기록."""

    def __init__(self, path: Path | str | None) -> None:
        self.path = Path(path) if path else None
        self.status = "running"
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def update(self, message: str, state: str = "running") -> None:
        from sage.text import nfc_user_text

        message = nfc_user_text(message)
        self.status = state
        if self.path is not None:
            line = json.dumps({"msg": message, "state": state}, ensure_ascii=False)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        if state == "failed":
            error(message)
        elif state == "completed":
            info(message)
        else:
            info(message)
