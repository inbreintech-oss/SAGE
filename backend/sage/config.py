import os
from pathlib import Path
from dotenv import load_dotenv

# .env 로드 — 이미 설정된 NARRATIX_HOME(컨테이너 /host/n2) 은 덮어쓰지 않음
load_dotenv(Path(__file__).parent.parent / ".env", override=False)

# NARRATIX_HOME — exec worker(Linux) 에서 .env 의 D:/… 와 /host/n2 혼선 방지
default_home = Path(__file__).parent.parent.resolve()


def resolve_narratix_home() -> Path:
    raw = (os.getenv("NARRATIX_HOME") or "").strip()
    if not raw:
        return default_home
    if os.name != "nt":
        if raw.startswith("/"):
            return Path(raw)
        # mounted .env 가 Windows 절대경로일 때 docker bind mount 루트
        if len(raw) >= 2 and raw[1] == ":":
            return Path("/host/n2")
    return Path(raw).resolve()


NARRATIX_HOME = resolve_narratix_home()

# 표준 경로 정의 — tools 하위 단일 루트 (assets/drafts 구분 없음)
TOOLS_DIR = NARRATIX_HOME / "tools"

# 하위 호환 alias (동일 경로)
DRAFTS_DIR = TOOLS_DIR
ASSETS_DIR = TOOLS_DIR

# 필수 디렉토리 보장
TOOLS_DIR.mkdir(parents=True, exist_ok=True)
