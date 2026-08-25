# n2oss

백엔드·프론트엔드를 하나의 저장소로 통합 관리하는 monorepo입니다.

| 경로 | 설명 |
|------|------|
| [`backend/`](backend/) | SAG-E API 서버 (FastAPI, Python 3.11+) |

프론트엔드는 추후 `frontend/` 등으로 추가될 예정입니다.

## 빠른 시작 (백엔드)

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env       # NARRATIX_HOME 등 수정
python main.py
```

자세한 설명은 [backend/README.md](backend/README.md)를 참고하세요.
