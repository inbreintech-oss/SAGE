# SAG-E Frontend

SAG-E Analytics 클라이언트 — React + TypeScript + Vite 기반 웹 UI입니다.

- **Repository:** [github.com/inbreintech-oss/SAGE](https://github.com/inbreintech-oss/SAGE) (`frontend/` 디렉터리)
- **Backend API:** [`../backend/`](../backend/) — 기본 `http://localhost:8090`

> 이 디렉터리는 **n2oss monorepo**의 프론트엔드 모듈입니다.

---

## Tech Stack

| 항목 | 기술 |
|------|------|
| Framework | React + TypeScript + Vite |
| Package manager | pnpm (workspace) |
| UI | Mantine ([@mantine/core](https://mantine.dev/core/package/)) |
| State | Zustand ([docs](https://zustand.docs.pmnd.rs/getting-started/introduction)) |
| Data fetching | TanStack Query ([@tanstack/react-query](https://tanstack.com/query/latest)) |
| Tables | TanStack Table ([@tanstack/react-table](https://tanstack.com/table/latest)) |

---

## 프로젝트 구조

```
frontend/
├── package.json           # workspace 루트 스크립트
├── pnpm-workspace.yaml
├── packages/
│   ├── app/               # admin-frontend (Vite 앱)
│   └── datatable/         # brewsync-datatable (내부 패키지)
├── nginx/                 # Docker 배포용 Nginx 설정
└── Dockerfile
```

---

## 설치 및 실행

`frontend/` 디렉터리에서:

```bash
pnpm install
pnpm run build:datatable
pnpm run dev:app
```

---

## 환경 변수

`packages/app/.env.example`을 복사해 `packages/app/.env`를 만듭니다.

| Name | Default | Description |
|------|---------|-------------|
| `BREWSYNC_CLIENT_PORT` | `5000` | Nginx listen 포트 (Docker 배포 시) |
| `BREWSYNC_API_URL` | `http://localhost:8090` | Backend API URL |
| `BREWSYNC_API_ENDPOINT` | `/api` | API 프록시 경로 |
| `VITE_SAGE_API_KEY` | (empty) | Backend `SAGE_API_KEY` 와 동일 (REST 인증 on 시) |

로컬 개발 시 백엔드를 먼저 기동하세요:

```bash
cd ../backend
python main.py
```

---

## 빌드

```bash
pnpm run build:datatable
pnpm run build:app
```

---

## Docker

```powershell
docker build -t sage-frontend .
docker run -p 5000:5000 `
  -e BREWSYNC_CLIENT_PORT=5000 `
  -e BREWSYNC_API_URL=http://localhost:8090/ `
  -e BREWSYNC_API_ENDPOINT=/api `
  sage-frontend
```

---

## 개발 가이드

### 페이지 작성

- 라우팅 단위로 `packages/app/src/pages/` 하위에 폴더 구성
- 레이아웃: `src/layouts`
- 라우트 등록: `src/libs/router/AppRouter.tsx` (LazyLoad + Code Splitting)

### Feature 작성

- API 호출: `@tanstack/react-query` 패턴
- 기능 단위: `packages/app/src/features/<FeatureName>/`
  - `api.ts`, `hooks.tsx`, `queries.ts`, `index.ts`

자세한 원본 가이드는 이전 SAGE.Frontend README 내용을 참고하세요.
