# 오픈소스 개발자 대회 — 프로젝트 보고서

## 프로젝트명

검증·재실행 가능 MCP 연동 분석 보고서 자동 생성 시스템

---

## 1. 프로젝트 소개

데이터 스키마를 기반으로 AI를 활용해 벤더 프리·오픈소스 Python 분석 보고서를 자동 생성하는 시스템이다.

- 사전 검토를 통한 신뢰성·재현성 향상 — 실행 전 분석 로직을 확인·검증하고, 발행 후 재실행(exec)으로 동일 분석을 반복한다.
- 조직에 적합한 보고서 공유 — 대화형 AI 보고서와 달리 발행된 보고서·데이터·MCP 도구를 팀·조직 단위로 공유·재사용한다.
- 벤더 종속 탈피·확장 연동 — BI 벤더에 묶이지 않고 오픈소스 Python과 MCP 연동으로 외부 API·데이터를 확장한다.

---

## 2. 개발 배경 및 목적

기존 대화형 AI 보고서는 일회성·블랙박스라 공유·감사·재현이 어렵고, BI 도구는 벤더·독점 포맷에 묶인다. 본 프로젝트는 데이터 스키마와 AI로 **파이썬 소스 활용 보고서**를 만들어, **사전 검토·발행·재실행**으로 신뢰·재현을 확보하고, **벤더 종속 보고서 체계를 벗어나** 최신 **MCP 보편 기술**을 접목하여 보고서 기능 확장이 가능하도록 한다.

**기존 방식의 한계**

- **대화형 AI 보고서:** 일회성·블랙박스, 개인 세션 — 공유·감사·재현 어려움, 보고서 **결과에 대한 후속 액션** 연계 불가
- **BI·벤더 보고서:** 독점 포맷·라이선스 종속 — 이전·오픈 연동 한계, 벤더 제공 기능 밖 **액션·알림** 확장 곤란

**본 프로젝트가 제시하는 방향**

- 파이썬 소스 + 사전 검토·발행·재실행 → 조직 공유·감사·재현
- Python OSS + **MCP 연동** → 보고서 **기능·액션**을 도구 추가만으로 확장

**MCP 확장 예 (보고서 결과 → 액션)**

- 「금일 3월 우수사원 보고서를 작성하고, 관련 임직원에게 SMS를 발송해 줘」처럼, 분석·보고 **이후 단계**(SMS·메일·슬랙·티켓 등)를 MCP 도구로 연결할 수 있다. BI·대화형 AI는 조회·문서에 그치기 쉬우나, 본 시스템은 **보고서 산출 → MCP 액션**까지 한 흐름으로 확장 가능하다.

---

## 3. 개발 환경

**하드웨어:** CPU 4코어 이상, RAM 16GB 이상, SSD 20GB 이상 / Windows·macOS·Linux

**소프트웨어:** Python 3.11+, Node.js 20+, Docker Desktop, AI API(Gemini/GPT/Claude 등)

**주요 기술:** FastAPI, React·Mantine, FerretDB+PostgreSQL, MCP(FastMCP), Docker exec pool

---

## 4. 시스템 구성 및 아키텍처

### 4.1 시스템 구성도

Word 제출용 그림: `docs/opdev-architecture.png` (본 문서와 동일 폴더)

```
[웹 클라이언트] ──REST/SSE──▶ [API 서버 :8090] ──▶ [메타 DB]
       │              Control Plane          │
       │         스키마·AI생성·검증·발행       │
       │                    │                 │
       │                    ├──▶ [AI API]     │
       │                    │                 │
       │                    ▼                 │
       │         [Docker Exec Pool :9001/9002]  │
       │              Data Plane               │
       │                    │                 │
       └────────────────────┼──▶ [MCP 게이트웨이 :8091] ──▶ [외부 API·SMS·데이터]
```

- **Control Plane (API :8090):** codegen·검증·DB·SSE — LLM 키·조직 데이터 보유
- **Data Plane (Docker exec):** 검증된 Python만 실행 — worker에 LLM key·DB 미전달
- **MCP 게이트웨이 (:8091):** 등록(assetize) 도구 HTTP 노출 — worker·보고서가 공통 참조
- **웹 클라이언트:** generate·publish·exec·조회 — SSE로 진행 실시간 표시

### 4.2 기술 스택 및 역할

**프레젠테이션**

- React 19, TypeScript, Vite — SPA·빌드
- Mantine 8 — UI 컴포넌트
- TanStack Query — API·SSE 연동, 보고서·데이터·도구 화면

**API·오케스트레이션 (Control Plane)**

- FastAPI, Pydantic — REST `/data`, `/report`, `/tool`, `/secret`
- SSE(EventSource) — generate·pangeaze 진행 스트리밍
- NodeV + report runner — plan DAG, 단계별 Python codegen, publish/exec
- Motor — FerretDB(Mongo 호환) 메타·상태 영속

**데이터·스키마**

- Pangea — CSV/XLSX·MCP 소스 → 통합 스키마(did-*), parquet
- 스키마 계약 — AI 프롬프트·validator 양쪽 주입

**실행·보안 (Data Plane)**

- docker_pool + worker daemon — warm worker(:9001, :9002)
- bind mount 결과 전달 — result.json, progress.ndjson
- API key 인증, worker env 최소화

**연동·확장**

- FastMCP — MCP HTTP 게이트웨이(:8091)
- assetize — 도구 namespace 등록·조직 공유
- LLM — Gemini/GPT/Claude/Cursor (환경 변수 교체)

**인프라**

- FerretDB 1.23 + PostgreSQL 16 — docker compose (n2-db)
- sage-exec — docker compose (n2-exec)

### 4.3 핵심 데이터 흐름

**① 데이터·스키마**

- upload(CSV/XLSX) → pangeaze(SSE) → schema/adapter/unify → parquet
- MCP 데이터 소스 → 스키마 연결, lazy 갱신

**② 보고서 생성 (generate)**

- 자연어 + 데이터셋 → plan DAG
- data → analyze → visual → narrative → release (단계별 Python 생성)
- validator 사전 검토 → plan·분석 로직·report.json 초안

**③ 발행·공유 (publish)**

- 검토·승인 후 발행 버전 고정
- 조직 내 목록·조회·공유 (대화형 세션과 구분)

**④ 재실행·재현 (exec)**

- 동일 Python 분석, 데이터만 갱신 — AI 재생성 없음
- Docker worker 격리 실행 → report.json 갱신·조회

**⑤ MCP 확장·액션**

- 도구 generate → assetize → 게이트웨이 mount
- 보고서·exec worker가 MCP URL로 SMS·API·외부 데이터 호출
- 예: 우수사원 보고서 생성 후 MCP SMS 도구로 임직원 알림

**⑥ 격리 원칙**

- 생성·스케줄링: API 프로세스
- 실행: Docker worker만 — MCP base URL·파일 mount만 허용

---

## 5. 프로젝트 세부 내용

### 5.1 핵심 기능 및 특장점

**데이터·스키마 통합** — CSV/XLSX·MCP 소스를 통합 스키마(did-*)·parquet로 등록. 스키마를 AI·검증기에 주입해 분석 일관성·재현성 확보.

**보고서 자동 생성** — 자연어 → plan DAG → data/analyze/visual/narrative/release 단계별 Python 생성. SSE로 진행 실시간 표시, DAG 병렬 처리.

**사전 검토·발행·재실행** — validator로 실행 전 검증 → publish(조직 공유) → exec(동일 분석 재현). 대화형 AI와 달리 **감사·정기 보고**에 적합.

**MCP 연동·액션 확장** — 도구 codegen·등록(assetize)·게이트웨이 공유. 예: 우수사원 보고 후 MCP SMS 도구로 임직원 알림.

**벤더 프리·격리 실행** — pandas/pyarrow 등 Python OSS. codegen은 API(:8090), 실행은 Docker worker(:9001/9002) — LLM key·DB worker 미노출.

**웹 UI** — React·Mantine에서 데이터·도구·보고서 생성·발행·재실행·미리보기 일원화.

### 5.2 개발 과정 (주요 단계 및 방법)

1. **요구·차별화 정의** — 스키마 기반, 사전 검토·재실행, MCP 연동, 조직 공유 방향 확정
2. **데이터·MCP** — Pangea 통합, FastMCP 게이트웨이, assetize 조직 공유
3. **보고서 파이프라인** — NodeV·plan DAG·단계별 codegen, publish/exec 분리
4. **검증·격리 실행** — validator·lesson 루프, docker_pool worker pool
5. **웹·통합** — React UI, SSE 연동, E2E(generate → publish → exec) 시연

개발 방법: FastAPI REST+SSE 오케스트레이션, instruction+validator 기반 NodeV 재시도, Docker bind mount로 exec 결과 handoff, OpenAPI(`/docs`)로 API 검증.

---

## 6. 구동 및 시연

### 6.1 실행 환경 준비

- `.env` — NARRATIX_HOME(프로젝트 루트), GEMINI_API_KEY(또는 GPT/Claude), SAGE_LLM_TYPE
- DB: `docker compose up -d` (FerretDB+PostgreSQL, mongo-express :8081)
- Exec pool: `docker compose -f docker-compose.exec.yml up -d --build` (worker :9001, :9002)
- API: `python main.py` → REST·SSE :8090, MCP 게이트웨이 :8091
- 웹: `pnpm install` → `pnpm run build:datatable` → `pnpm run dev:app` (API URL을 :8090에 맞출 것)

### 6.2 시연 시나리오 및 결과물

**시각 자료:** 시스템 구성도 — `docs/opdev-architecture.png` (Word 삽입용)

**시연 순서**

1. **데이터** — CSV 업로드 → Pangea 통합(SSE) → 통합 데이터 조회
2. **보고서 생성** — 데이터셋 + 자연어 질의 → generate(SSE: planned → executed → completed)
3. **사전 검토** — 생성된 분석 로직 확인 후 publish
4. **재실행·조회** — exec로 동일 보고서 재실행, 레이아웃 미리보기에서 report.json 렌더
5. **MCP** — 외부 API·SMS 도구 등록(assetize) → 보고서·exec에서 연계

**결과물:** `reports/{rid}/` — plan.json, 단계별 Python 분석, report.json(차트·서술·레이아웃). 발행본은 조직 내 목록·재실행·조회 가능.

### 6.3 테스트 방법

- OpenAPI — http://127.0.0.1:8090/docs 수동 REST·SSE 확인
- `_scripts/test_report_generate.py` — 보고서 generate E2E
- `_scripts/test_tool_exec.py` — MCP·docker exec smoke
- worker health — http://127.0.0.1:9001/health idle 확인

**시연 체크:** DB·exec pool 기동 → LLM key 유효 → generate 완료 → publish → exec 재현 → MCP 게이트웨이 연동

---

## 7. 기대효과 및 활용 분야

### 기대효과

이 시스템을 쓰면 다음과 같은 효과를 기대할 수 있다.

- **시간·비용 절감** — 엑셀·SQL·보고서 작성에 쓰던 시간을 줄이고, 한 번 만든 보고서는 데이터만 바꿔 **다시 실행**하면 된다.
- **누구나 활용** — 데이터 전문가가 아니어도 **말로 요청**하면 분석·차트·글까지 담긴 보고서를 받을 수 있다.
- **믿고 쓸 수 있음** — AI가 만든 내용을 **미리 확인**한 뒤 배포하고, 같은 방식으로 **반복 실행**해 결과가 흔들리지 않게 한다.
- **팀·회사 단위 공유** — 챗봇 대화처럼 개인만 보는 것이 아니라, **만들어 둔 보고서를 조직에서 함께** 본다.
- **벤더에 묶이지 않음** — 특정 BI·AI 회사 포맷에 종속되지 않고, **오픈소스 Python**으로 분석 내용을 유지한다.
- **기능 확장** — 주가·SMS·슬랙 등 **외부 연동**을 붙여 「보고서 작성 → 알림 발송」처럼 **일까지 이어**갈 수 있다.

### 활용 분야

금융(개인 재무·소상공인 경영), 부동산 투자, 의료·건강, 교육·학습, 채용, 웹·앱·SNS 마케팅, 제조·공정, ESG, 보험, 스포츠 등 **데이터만 있으면** 같은 방식으로 **정기 보고·현황 브리핑**을 자동화할 수 있다.

---

## 8. 기타

### 8.1 혁신성 및 차별성

- **대화형 AI와 다름** — 챗은 일회성·결과 들쭉날쭉. 본 시스템은 **미리 확인 → 발행 → 같은 분석 재실행**, **팀·조직 공유**.
- **BI·상용과 다름** — 벤더 포맷 종속 없이 **Python OSS**. MCP로 「보고 + SMS 발송」처럼 **후속 액션** 연결.
- **기술** — 데이터 스키마로 AI·검증 기준 통일, 보고서 **생성(API)·실행(Docker)** 분리로 안전 운영.

### 8.2 한계점 및 향후 발전 로드맵

**한계:** 최초 생성·검증에 시간·비용 / worker 2대 / 권한·승인 UI 미흡 / MCP 연동 확대 필요

**로드맵:** 승인·부서 권한 → 정기 자동 실행 → 조직 공유 레지스트리 → worker·K8s·감사 로그

### 8.3 소감 및 후기

“AI가 잘 쓰는가”보다 **“믿고, 같이 쓰고, 내일도 같은 결과인가”** 가 핵심이었다. 미리 확인·발행·재실행과 Python·MCP를 한 흐름으로 묶었고, Docker·동시 사용자 등 **운영을 전제로 설계**하니 조직용에 가까워졌다.

---

## 9. SBOM (소프트웨어 자재명세서)

**1. fastapi** 0.135.1 · MIT · https://github.com/fastapi/fastapi — API·SSE 서버, 보고서·데이터·도구 오케스트레이션

**2. fastmcp** 2.14.1 · MIT · https://github.com/jlowin/fastmcp — MCP 게이트웨이, 외부 API·SMS 등 도구 연동·확장

**3. google-genai** 1.56.0 · Apache-2.0 · https://github.com/googleapis/python-genai — AI 보고서·데이터·도구 자동 생성(GPT/Claude 등 교체 가능)

**4. pandas** 2.3.2 · BSD-3-Clause · https://github.com/pandas-dev/pandas — Python 오픈소스 데이터 분석·보고서 exec

**5. react** 19.1.1 · MIT · https://github.com/facebook/react — 웹 UI(데이터·보고서 생성·발행·재실행)

---

문서 버전: 2026-08 — 오픈소스 개발자 대회 제출용
