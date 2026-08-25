"""프로젝트 전역 경로·환경 설정.

import 시점에 uploads/dump/runs/tools 디렉터리를 생성하고 .env 를 로드합니다.
API(8090)와 MCP 게이트웨이(8091 = port+1)의 bind 주소도 여기서 정의합니다.
"""

import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

root_path = Path(os.environ.get("NARRATIX_HOME", os.path.dirname(os.path.abspath(__file__))))

# --- 워크스페이스 경로 (NARRATIX_HOME 과 동일 루트 권장) ---
tools_path = root_path / 'tools'       # MCP 도구 (assetize 후 main.py)
rscs_path = root_path / 'resources'      # 샘플 CSV 등
dump_path = root_path / 'dump'           # TaskContext — plan_id hex 별 context.json
uploads_path = root_path / 'uploads'     # POST /data/upload 임시 저장
runs_path = root_path / 'runs'           # published 보고서 exec 산출물
# SAGE_NODES_PATH 로 외부 nodes/ 트리 지정 가능 (기본: ./nodes)
nodes_path = Path(os.environ.get("SAGE_NODES_PATH", root_path / "nodes"))

cached = False  # LLM 응답 캐시 (utils.cache) — 운영 시 True 검토

# import 시점에 필수 디렉터리 보장 (없으면 자동 생성)
os.makedirs(tools_path, exist_ok=True)
os.makedirs(dump_path, exist_ok=True)
os.makedirs(uploads_path, exist_ok=True)
os.makedirs(runs_path, exist_ok=True)

load_dotenv(find_dotenv())

# REST API auth — SAGE_API_AUTH_ENABLED=on 일 때만 SAGE_API_KEY 검사 (기본 off, 로컬/UI 디버깅)
_sage_api_auth_raw = os.environ.get("SAGE_API_AUTH_ENABLED", "off").strip().lower()
sage_api_auth_enabled = _sage_api_auth_raw in ("1", "true", "yes", "on")
sage_api_key = os.environ.get("SAGE_API_KEY", "").strip()

# Exec isolation — docker_pool only (host /host/n2 bind mount + warm pool)
sage_exec_driver = os.environ.get("SAGE_EXEC_DRIVER", "docker_pool").strip().lower()
sage_exec_timeout_sec = int(os.environ.get("SAGE_EXEC_TIMEOUT_SEC", "600"))
sage_exec_stall_sec = int(os.environ.get("SAGE_EXEC_STALL_SEC", "45"))
sage_exec_pool_acquire_sec = float(os.environ.get("SAGE_EXEC_POOL_ACQUIRE_SEC", "120"))
sage_exec_max_jobs_per_container = int(os.environ.get("SAGE_EXEC_MAX_JOBS_PER_CONTAINER", "50"))
sage_exec_docker_image = os.environ.get("SAGE_EXEC_DOCKER_IMAGE", "sage-exec:latest").strip()
# Worker → host MCP (Docker 내부). 비어 있으면 get_transport_path 가 localhost:8091 사용
sage_mcp_base_url = os.environ.get("SAGE_MCP_BASE_URL", "").strip().rstrip("/")
# MCP gateway bind — docker worker 가 host.docker.internal 로 접근하려면 0.0.0.0
_default_mcp_bind = "0.0.0.0" if sage_exec_driver == "docker_pool" else host
sage_mcp_bind_host = os.environ.get("SAGE_MCP_BIND_HOST", _default_mcp_bind).strip()

# FastAPI API 서버 bind (MCP 게이트웨이는 sage/mcp 에서 port+1 사용)
host = 'localhost'  # '0.0.0.0'   # '192.168.0.150'
port = 8090
mcp_path = ''  # 레거시 — 현재는 tools/{route}/ HTTP mount 방식
