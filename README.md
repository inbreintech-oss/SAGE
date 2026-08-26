# n2oss

백엔드·프론트엔드를 하나의 저장소로 통합 관리하는 monorepo입니다.

| 경로 | 설명 |
|------|------|
| [`backend/`](backend/) | SAG-E API 서버 (FastAPI, Python 3.11+) |
| [`frontend/`](frontend/) | SAG-E Analytics 클라이언트 (React + TypeScript + Vite) |

**Repository:** [github.com/inbreintech-oss/SAGE](https://github.com/inbreintech-oss/SAGE)

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

- [backend/README.md](backend/README.md) — API 서버, Docker DB, 환경 변수
- [frontend/README.md](frontend/README.md) — UI 개발, 빌드, Docker 배포
