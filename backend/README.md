# SAG-E

**Schema-Augmented Generation & Execution** — LLM과 MCP를 활용해 데이터 통합, 도구 생성, 보고서 codegen·실행까지 이어지는 분석 프레임워크입니다.

스키마 기반 데이터 격리로 분석 환경의 일관성을 유지하고, 검증(validation)과 자가 학습(lesson) 루프를 통해 생성 코드의 신뢰성을 높입니다.

- **License:** [MIT](LICENSE)
- **Repository:** [github.com/inbreintech/SAGE.py](https://github.com/inbreintech/SAGE.py)
- **Maintainer:** [Inbrein](https://github.com/inbreintech) — inbreintech@inbrein.com

---

## 주요 기능

| 영역 | 설명 |
|------|------|
| **데이터 (Pangea)** | 파일·MCP 도구 소스를 통합 스키마(`did-*`)로 등록·갱신 |
| **도구 (MCP Tool)** | LLM codegen → 검증 → assetize → `/tool/exec` 실행 |
| **보고서 (Report)** | Plan DAG → 태스크별 codegen → 병렬 실행 → layout/release |
| **NodeV** | instruction + validator + `validated.md` 기반 재시도·학습 |
| **LLM** | Gemini / GPT / Claude / Cursor (`SAGE_LLM_TYPE`) |

---

## 요구 사항

- **Python** 3.11.7+
- **Docker Desktop** (FerretDB + PostgreSQL)
- LLM API 키 (Gemini 등, `.env` 참고)

---

## 설치

```bash
git clone https://github.com/inbreintech/SAGE.py.git
cd SAGE.py

python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

---

## 환경 변수

프로젝트 루트에 `.env` 파일을 만들고 [`.env.example`](.env.example)를 참고해 설정합니다.

```env
NARRATIX_HOME=/path/to/SAGE.py    # 프로젝트 루트 절대 경로
GEMINI_API_KEY=your-key-here
SAGE_LLM_TYPE=gemini              # gemini | gpt-5 | claude | cursor
SAGE_LLM_TIMEOUT_SEC=600          # codegen 대용량 attach 시 권장
SAGE_SECRET_ENCRYPTION_KEY=       # SecretKey DB 암·복호화 (SAGE_API_KEY 와 별도)
SAGE_API_AUTH_ENABLED=off         # on 일 때만 REST API-Key 검사
LOG_LEVEL=INFO
```

| 변수 | 설명 |
|------|------|
| `NARRATIX_HOME` | 워크스페이스 루트 (`tools/`, `reports/`, `nodes/` 기준) |
| `SAGE_LLM_TYPE` | 기본 LLM 백엔드 |
| `SAGE_CURSOR_*` | Cursor Agent 사용 시 모델·런타임·타임아웃 |
| `GPT_API_KEY` / `CLAUDE_API_KEY` | 해당 LLM 선택 시 |
| `SAGE_SECRET_ENCRYPTION_KEY` | 등록된 API 키(증권사 APP_KEY 등) 암·복호화 |
| `SAGE_API_AUTH_ENABLED` / `SAGE_API_KEY` | REST 인증. 기본 off (로컬·UI) |

**커밋하지 말 것:** `.env`, 실제 API 키, `tools/` 생성물, `logs/`, `dump/`. 키는 `/secret/register` 로 등록하고 도구 생성 시 `secret_id` (`sk-*`) 만 넘긴다.

---

## 데이터베이스 (FerretDB + PostgreSQL)

DB 스택과 exec pool은 **Compose 프로젝트가 분리**되어 있습니다 (`n2-db` / `n2-exec`).
exec pool 기동·recycle 시 DB 컨테이너가 내려가지 않도록 분리해 두었습니다.

```bash
# DB (postgres + ferretdb + mongo-express) — 한 번 띄우면 restart: unless-stopped
docker compose up -d

# Exec warm pool (report/unify/tool 격리) — API와 별도
docker compose -f docker-compose.exec.yml up -d --build
```

| 서비스 | 용도 |
|--------|------|
| PostgreSQL | FerretDB 백엔드 저장소 |
| FerretDB | MongoDB 호환 API |
| mongo-express | 웹 UI — http://localhost:8081/ (기본: `admin` / `pass`, `docker-compose.yml` 참고) |

---

## 서버 실행

[`cfg.py`](cfg.py)에서 bind 주소·포트를 변경할 수 있습니다 (기본 `localhost:8090`).

```bash
python main.py
```

또는:

```bash
uvicorn main:app --host 127.0.0.1 --port 8090
```

실행 후 **OpenAPI 문서:** http://127.0.0.1:8090/docs

---

## API 개요

| Prefix | 대표 엔드포인트 | 설명 |
|--------|-----------------|------|
| `/data` | `POST /pangeaze` | 데이터셋 통합 (SSE) |
| `/data` | `POST /upload` | 파일 업로드 |
| `/tool` | `POST /generate`, `/exec`, `/assetize` | 도구 codegen·실행·자산화 (`generate` 시 `secret_id`) |
| `/report` | `POST /generate`, `/exec`, `/publish` | 보고서 생성·실행·발행 |
| `/secret` | `POST /register`, `/list` | API 키 등록 (값은 응답에 포함하지 않음) |

보고서·데이터 생성 API는 **Server-Sent Events(SSE)** 로 진행 상태를 스트리밍합니다.

---

## 프로젝트 구조

```
.
├── main.py              # FastAPI 진입점
├── cfg.py               # 경로·호스트 설정
├── routers/             # REST API (data, report, tool, secret)
├── sage/                # 코어 라이브러리
│   ├── llm/             # LLM 추상화·팩토리
│   ├── report/          # 보고서 파이프라인 (runner, layout, validators)
│   ├── nodes/           # NodeV 프레임워크·학습
│   ├── mcp/             # MCP 클라이언트·서버
│   ├── secret/          # SecretKey 조회·암복호화
│   ├── tool/            # dump·smoke·generate 가이드
│   └── data/            # Pangea·스키마 계약
├── nodes/               # LLM 노드 (plan, task, pangeaze, tool …)
├── tools/               # assetize된 MCP 도구
└── reports/             # 생성된 보고서 산출물
```

---

## 문서

| 문서 | 내용 |
|------|------|
| [docs/docs.md](docs/docs.md) | API·개발 디버그 가이드 |
| [docs/tools.md](docs/tools.md) | MCP 도구 작성·assetize |
| [docs/nodes.md](docs/nodes.md) | 노드(instruction, validated.md) 구조 |
| [docs/exec-isolation.md](docs/exec-isolation.md) | Exec 격리 작업 명세 (LLM codegen worker 분리) |

---

## 라이선스

[MIT License](LICENSE) — Copyright (c) 2026 Inbrein
