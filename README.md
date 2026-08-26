# n2oss — SAG-E Monorepo

**SAG-E** (Schema-Augmented Generation & Execution)는 LLM과 MCP(Model Context Protocol)를 활용해 **데이터 통합 → 도구 생성 → 분석 보고서 codegen·실행**까지 이어지는 오픈소스 분석 프레임워크입니다.

데이터 스키마를 기준으로 AI가 Python 분석·보고서 소스를 생성하고, **사전 검증·발행·재실행(exec)** 으로 신뢰성과 재현성을 확보합니다. BI 벤더에 묶이지 않고 MCP로 외부 API·액션(SMS, 슬랙 등)까지 확장할 수 있습니다.

**Repository:** [github.com/inbreintech-oss/SAGE](https://github.com/inbreintech-oss/SAGE)

---

## 전체 구성

| 구분 | 역할 | 포트·경로 |
|------|------|-----------|
| **Frontend** | React 웹 UI — 데이터·도구·보고서 관리 | `frontend/` → Backend API 연동 |
| **Backend (Control plane)** | FastAPI — LLM codegen, 검증, SSE, DB | `:8090` — `backend/` |
| **Exec pool (Data plane)** | Docker worker — 생성된 Python만 실행 | `:9001`, `:9002` |
| **MCP Gateway** | assetized 도구 HTTP 노출 | `:8091` |
| **Meta DB** | FerretDB + PostgreSQL | `:27017`, mongo-express `:8081` |

> *생성은 control plane, 실행은 data plane.* 상세 아키텍처는 [backend/docs/docs.md](backend/docs/docs.md) 참고.

---

## 주요 기능

| 영역 | 설명 |
|------|------|
| **데이터 (Pangea)** | 파일·MCP 도구 소스를 통합 스키마(`did-*`)로 등록·갱신 |
| **도구 (MCP Tool)** | LLM codegen → 검증 → assetize → `/tool/exec` 실행 |
| **보고서 (Report)** | Plan DAG → 태스크별 codegen → 병렬 실행 → layout/release |
| **NodeV** | `instruction.md` + validator + `validated.md` 기반 재시도·학습 루프 |
| **LLM** | Gemini / GPT / Claude / Cursor (`SAGE_LLM_TYPE`) |

---

## Monorepo 구조

| 경로 | 설명 |
|------|------|
| [`backend/`](backend/) | SAG-E API 서버 (FastAPI, Python 3.11+) |
| [`frontend/`](frontend/) | SAG-E Analytics 클라이언트 (React + TypeScript + Vite) |

---

## 요구 사항

- **Python** 3.11.7+ · **Node.js** 20+ · **pnpm**
- **Docker Desktop** (FerretDB + PostgreSQL, exec worker pool)
- LLM API 키 (Gemini / GPT / Claude 등)

---

## 빠른 시작

### Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env       # NARRATIX_HOME 등 수정
python main.py
```

→ http://127.0.0.1:8090/docs

### Frontend

```bash
cd frontend
pnpm install
pnpm run build:datatable
pnpm run dev:app
```

→ Backend API (`http://localhost:8090`) 연동

---

## 문서

| 문서 | 내용 |
|------|------|
| [backend/README.md](backend/README.md) | API 서버 설치, Docker DB, 환경 변수 |
| [frontend/README.md](frontend/README.md) | UI 개발, 빌드, Docker 배포 |
| [backend/docs/docs.md](backend/docs/docs.md) | 개발 가이드, 아키텍처, API·SSE·exec 흐름 |
| [backend/docs/tools.md](backend/docs/tools.md) | MCP 도구 작성·assetize |
| [backend/docs/nodes.md](backend/docs/nodes.md) | NodeV(instruction, validated.md) 구조 |
| [backend/docs/exec-isolation.md](backend/docs/exec-isolation.md) | Exec 격리·Docker worker pool |
| [backend/docs/opdev.md](backend/docs/opdev.md) | 프로젝트 소개·개발 배경 (대회 보고서) |
