"""FastMCP client — session pool, tool calls, gateway app, and tool spec loading.

이 모듈은 두 역할을 한 파일에 담는다.

1. **호출측(Client)** — ``get_client`` / ``call`` / ``load_tools_spec``
   report·data executor 가 MCP 도구를 부를 때 쓰는 세션 풀. asyncio 루프마다
   별도 Client 를 캐시하고, WinError 10054 등 끊긴 소켓은 좀비로 판정 후
   폐기·재연결한다.

2. **게이트웨이(Server)** — ``create_app`` / lazy mount / ``warmup_mcp_tool``
   assetized 도구의 ``main.py`` 를 FastMCP http_app 으로 mount 하는 계층형
   MCP 게이트웨이. 기동 시 이미 assetized 인 것을 mount 하고, 런타임에
   assetize 된 것은 첫 HTTP 요청(또는 warmup) 때 lazy mount.

전송 경로 결정: ``get_transport_path`` — assetized → HTTP(cfg.port+1),
그 외 → tools/{path}/main.py stdio 서브프로세스.
"""

import asyncio
import json
import os
import time
import traceback
from typing import Dict, Any, List
import importlib.util
import numpy as np
from fastapi import FastAPI
from fastmcp import FastMCP, Client  # Import the client
from fastmcp.client.transports import PythonStdioTransport
from fastmcp.utilities.logging import configure_logging
from contextlib import asynccontextmanager, AsyncExitStack

import logging
from sage.config import TOOLS_DIR
from sage.errs import format_exception
from sage.logg import error, info
from sage.tool.metadata import is_assetized, tool_dir
from pydantic import TypeAdapter
import cfg

configure_logging(level='CRITICAL')

# Timeout 등 로깅 차단
# mcp 통신 라이브러리 내부의 SSE 파싱 에러 로그 출력을 완전히 차단
logging.getLogger("mcp.client.streamable_http").setLevel(logging.CRITICAL)
logging.getLogger("anyio").setLevel(logging.CRITICAL)

_PROJECT_ROOT = str(cfg.root_path.resolve())


def _stdio_subprocess_env() -> dict[str, str]:
    """stdio MCP 서브프로세스 — worker env(SAGE_MCP_BASE_URL 등) + PYTHONPATH 전파.

    Docker exec worker 안에서 assetized 도구(kis/stock)를 HTTP로 부르려면
    stdio로 띄운 중간 도구(tm-stock-financials 등)에도 SAGE_MCP_BASE_URL 이
    있어야 한다. 없으면 localhost:8091 로 붙어 컨테이너 내부에서 연결 실패한다.
    """
    from sage.config import resolve_narratix_home

    env = os.environ.copy()
    root = str(resolve_narratix_home())
    parts = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
    if root not in parts:
        parts.insert(0, root)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    env.setdefault("PYTHONUTF8", "1")
    return env


def create_mcp_client(target_path: str) -> Client:
    """HTTP URL 또는 stdio(main.py) 경로에 맞는 FastMCP Client 를 생성합니다."""
    if target_path.startswith("http"):
        return Client(target_path)

    if target_path.endswith(".py") and os.path.isfile(target_path):
        transport = PythonStdioTransport(
            script_path=target_path,
            env=_stdio_subprocess_env(),
            cwd=_PROJECT_ROOT,
        )
        return Client(transport)

    return Client(target_path)

# async def _call(cl: Client, tool_name: str, tool_args: Dict[str, Any]) -> Any:
#     """
#     FastMCP 서버에 Tool Call을 요청하고, 함수 structured 결과값(raw value)을 반환.
#     (async with 문맥 관리자를 사용하여 연결 오류를 수정함)
#     """
#     try:
#         res = None
#         async with cl as c:  # client.call_tool 실행
#             raw_result = await c.call_tool(tool_name, tool_args)
#             res = raw_result.structured_content  # ['result'] if 'result' in raw_result.structured_content else raw_result.structured_content
#         return res
#     except Exception as e:
#         # RuntimeError가 아닌 다른 예외 발생 시 처리
#         print(f"오류 발생: {type(e).__name__}: {e}")
#         return None

def convert_numpy_types(obj: Any) -> Any:
    """Recursively convert NumPy scalars and arrays to native Python types."""
    if isinstance(obj, np.generic):
        return obj.item()

    # 2. NumPy 배열 처리
    if isinstance(obj, np.ndarray):
        return [convert_numpy_types(i) for i in obj.tolist()]

    # 3. 딕셔너리 처리 (키가 NumPy 타입일 가능성 대비)
    if isinstance(obj, dict):
        return {
            (k.item() if isinstance(k, np.generic) else str(k)): convert_numpy_types(v)
            for k, v in obj.items()
        }

    # 4. 반복 가능한 컬렉션 처리 (list, tuple, set)
    if isinstance(obj, (list, tuple, set)):
        return [convert_numpy_types(i) for i in obj]

    return obj

# Pydantic v2 TypeAdapter
ANY_ADAPTER = TypeAdapter(Any)

# def to_plain_dict(obj):
#     if hasattr(obj, 'model_dump'):
#         return obj.model_dump(mode='json')
#
#     if hasattr(obj, 'dict'):  # v1 대응
#         return obj.dict()
#
#     # 2. 리스트인 경우 (내부에 Root가 숨어있을 수 있음)
#     if isinstance(obj, list):
#         return [to_plain_dict(item) for item in obj]
#
#     # 3. 딕셔너리인 경우 (Value에 Root가 숨어있을 수 있음)
#     if isinstance(obj, dict):
#         return {k: to_plain_dict(v) for k, v in obj.items()}
#
#     if type(obj).__name__ == "Root":  # == types.Root
#         return vars(obj)
#
#     return obj

def universal_serializer(obj: Any) -> Any:
    """
    NumPy 타입을 처리한 후 Pydantic v2를 사용하여 JSON 호환 타입으로 변환합니다.
    """
    converted_obj = convert_numpy_types(obj)

    # Pydantic v2에서 mode='json'은 객체를 dict/list/str/int 등 JSON 기본 타입으로 강제 변환합니다.
    # 이 과정에서 처리되지 않은 타입이 있으면 에러가 발생하므로
    # 위 convert_numpy_types에서 최대한 정제되어야 합니다.
    return ANY_ADAPTER.dump_python(
        converted_obj,
        mode='json'
    )

async def close_all_sessions():
    """프로그램 종료 시 모든 세션을 안전하게 닫습니다.

    ``__aenter__`` 로 연 Client 는 반드시 ``__aexit__`` 로 닫아야 stdio
    서브프로세스·HTTP 소켓이 남지 않는다. 프로세스 shutdown 훅에서 호출.
    """
    for cl in _CLIENT_SESSIONS.values():
        await cl.__aexit__(None, None, None)
    _CLIENT_SESSIONS.clear()


# ---------------------------------------------------------------------------
# 세션 풀
#
# 키: ``f"{id(asyncio_loop)}_{path}"``
#   - 같은 path 라도 event loop 가 다르면 Client 를 공유하면 안 된다.
#     (다른 스레드/전용 루프에서 await 하면 "attached to a different loop")
#   - path 는 논리적 도구 route (예: kis/stock). transport URL/파일은
#     get_transport_path 가 매번 해석.
#
# 값: 이미 ``__aenter__`` 된 live FastMCP Client.
# call() 실패·좀비 판정 시 pop + __aexit__ 로 제거하고 다음 시도에서 재생성.
# ---------------------------------------------------------------------------
_CLIENT_SESSIONS: Dict[str, Client] = {}

# async def get_client(path: str, transport: str = 'auto') -> Client:
#     # 현재 실행 중인 루프의 ID를 추출하여 키 생성
#     # 이 키는 메인 스레드와 전담 스레드를 완벽히 분리해줍니다.
#     current_loop = asyncio.get_running_loop()
#     session_key = f"{id(current_loop)}_{path}"
#
#     client = _CLIENT_SESSIONS.get(session_key)
#     # print(f"[Pangea] [CACHE HIT] Session: {session_key} | ClientID: {id(client)}")
#
#     # 세션이 없거나 이미 닫혀 있다면 새로 생성
#     if not client:
#         # 1. 전송 경로 및 방식 결정
#         target_path = get_transport_path(path, transport=transport)
#
#         # 2. HTTP 여부에 따른 분기 처리
#         if target_path.startswith('http'):
#             # HTTP/SSE 방식 클라이언트
#             cl = Client(target_path)
#             # HTTP는 연결 확인이 빠르므로 타임아웃을 짧게 잡을 수 있습니다.
#             await asyncio.wait_for(cl.__aenter__(), timeout=120.0)
#         else:
#             # stdio 방식 (로컬 python main.py 실행)
#             cl = Client(target_path)
#             # 로컬 프로세스 실행은 가상환경 로드 등으로 인해 더 긴 시간이 필요할 수 있습니다.
#             await asyncio.wait_for(cl.__aenter__(), timeout=120.0)
#
#         _CLIENT_SESSIONS[session_key] = cl
#         return cl
#
#     return client

async def get_client(path: str, transport: str = 'auto') -> Client:
    """Return a cached or new FastMCP client for ``path`` (HTTP URL or stdio ``main.py``).

    Args:
        path: Tool route id, file path, or HTTP endpoint.
        transport: ``auto``, ``stdio``, or ``http`` — resolved via :func:`get_transport_path`.

    Returns:
        Connected :class:`fastmcp.Client` bound to the current asyncio loop.

    좀비(zombie) 세션 처리
    ----------------------
    풀에 Client 가 있어도 상대 게이트웨이 재시작·stdio 프로세스 사망·HTTP keep-alive
    끊김 등으로 ``is_connected()`` 가 False 이거나 예외를 낼 수 있다. 이 상태의
    Client 를 재사용하면 call_tool 이 즉시 실패하거나 hang 한다.

    절차: is_connected 실패 → 풀에서 pop → ``__aexit__`` 로 OS 소켓/서브프로세스
    반납(실패 무시) → client=None 으로 내려가 새 연결 생성.
    연결 ``__aenter__`` 타임아웃 30초 — 실패 시 풀에 반쯤 넣은 키를 pop 하고
    RuntimeError 로 래핑해 올린다.
    """
    current_loop = asyncio.get_running_loop()
    session_key = f"{id(current_loop)}_{path}"
    client = _CLIENT_SESSIONS.get(session_key)

    # 좀비 세션 검증 로직
    if client:
        try:
            is_alive = client.is_connected()
        except Exception:
            is_alive = False

        if not is_alive:
            cl = _CLIENT_SESSIONS.pop(session_key, None)
            if cl:
                try:
                    await cl.__aexit__(None, None, None)
                except:
                    pass
            client = None

    if client:
        return client

    # 새로운 클라이언트 생성
    target_path = get_transport_path(path, transport=transport)
    client = create_mcp_client(target_path)

    try:
        await asyncio.wait_for(client.__aenter__(), timeout=30.0)
        _CLIENT_SESSIONS[session_key] = client
        return client
    except Exception as e:
        _CLIENT_SESSIONS.pop(session_key, None)
        detail = format_exception(
            e,
            context=(
                f"FastMCP 연결 실패 [{path}] "
                f"(transport={transport}, target={target_path})"
            ),
        )
        raise RuntimeError(detail) from e


async def call(path: str, tool_name: str, tool_args: dict, transport='auto', *args, **kwargs) -> Any:
    """Invoke an MCP tool and return ``structured_content`` (with reconnect retries).

    Args:
        path: Tool route or transport target passed to :func:`get_client`.
        tool_name: Registered MCP tool name.
        tool_args: JSON-serializable arguments (merged with ``kwargs``).
        transport: Transport hint for path resolution.

    Returns:
        Parsed tool result, or raw response when no structured payload exists.

    재시도 루프 설계
    ----------------
    Windows 에서 MCP HTTP/stdio 가 자주 내는 ``WinError 10054``(연결 강제 종료)·
    Timeout·ConnectionReset 은 *같은* 세션을 재사용하면 연속 실패한다.
    그래서 실패 시:

    1. 해당 session_key 를 풀에서 pop
    2. ``__aexit__`` 로 소켓을 OS 에 반납 (이미 죽은 소켓 예외는 무시)
    3. 0.5s backoff 후 다음 attempt → get_client 가 새 연결을 염

    인자는 ``universal_serializer`` 로 NumPy/Pydantic 을 JSON 호환으로 정리한 뒤
    넘긴다(도구 쪽 schema 검증 통과용). structured_content 가 없으면 raw 반환.
    참고: 첫 except 가 Exception 을 이미 잡으므로 아래 두 번째 except 는
    사실상 도달하지 않지만 기존 분기 형태를 유지한다.
    """
    combined_args = tool_args if (tool_args and isinstance(tool_args, dict)) else {}
    if kwargs:
        combined_args.update(kwargs)
    clean_args = universal_serializer(combined_args)

    current_loop = asyncio.get_running_loop()
    session_key = f"{id(current_loop)}_{path}"

    # WinError 10054 등 소켓 끊김 시 세션 폐기 후 재연결 (최대 3회)
    last_err = None
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # 안전하게 세션 확보
            client = await get_client(path, transport=transport)

            # 통신 실행 (타임아웃 30초)
            raw_result = await asyncio.wait_for(
                client.call_tool(tool_name, clean_args),
                timeout=30
            )
            # raw_result = await client.call_tool(tool_name, clean_args)  # 무한 대기 상태 진입

            # 결과 반환
            return getattr(raw_result, 'structured_content', raw_result)

        except (asyncio.TimeoutError, ConnectionResetError, Exception) as e:
            # 에러 발생 시 '설거지'를 확실히 합니다.
            # 딕셔너리에서 지우기 전에 OS에게 소켓을 명시적으로 반납합니다.
            cl = _CLIENT_SESSIONS.pop(session_key, None)
            if cl:
                try:
                    # async with의 '종료' 부분을 수동 격발하여 10054 원천 차단
                    await cl.__aexit__(None, None, None)
                except:
                    pass  # 이미 터진 소켓은 무시

            # 마지막 오류 상태
            last_err = e

            # 첫 번째 실패라면 잠시 숨을 고르고 서버를 새로 띄우도록 유도
            await asyncio.sleep(0.5)
            continue
        except Exception as e:
            # err_mag = traceback.format_exc()
            last_err = e
            continue

    detail = format_exception(
        last_err,
        context=(
            f"Pangea 도구 호출 실패 [{path}] "
            f"(tool={tool_name}, transport={transport}, attempts={max_attempts})"
        ),
    )
    raise RuntimeError(detail) from last_err

def tool_specs_for_llm(full_tool_list: List[Any]) -> List[Dict[str, Any]]:
    """
    FastMCP list_tools() 결과에서 LLM 호출에 필요한 핵심 정보만을 추출합니다.

    Args:
        full_tool_list: list_tools() 호출 결과로 반환된 전체 Tool 객체 리스트.

    Returns:
        List[Dict[str, Any]]: name, description, inputSchema, outputSchema 만을 포함하는 정제된 도구 스펙 리스트.
    """

    def _drop(s: dict):
        if 'x-fastmcp-wrap-result' in s:
            _ = s.pop('x-fastmcp-wrap-result')
        return s

    llm_specs = []

    for tool in full_tool_list:
        # LLM에게 필요한 핵심 필드만 추출
        spec = {
            "name": tool.name,
            # description 필드는 LLM이 도구의 용도를 이해하는 데 필수적입니다.
            "description": tool.description,
            "input": tool.inputSchema
        }

        # outputSchema는 Optional이므로, 존재하는 경우에만 추가합니다.
        output_schema = tool.outputSchema
        if output_schema is not None:
            spec['output'] = output_schema  # _drop(output_schema)

        # title 필드는 종종 description보다 더 간결한 요약 정보를 제공하므로,
        # LLM에게 유용할 수 있어 포함하는 것이 일반적입니다. (선택 사항)
        title = tool.title
        if title is not None:
            spec["title"] = title

        # 모든 필수 필드가 존재하는지 확인 (name과 inputSchema는 required임)
        if spec["name"] and spec["input"]:
            llm_specs.append(spec)

    return llm_specs

def find_all_tool_files(tool_directory: str) -> List[str]:
    """
    주어진 디렉토리와 그 하위 디렉토리를 재귀적으로 탐색하여
    모든 Python 파일(.py)의 전체 경로를 리스트로 반환합니다.

    Args:
        tool_directory: 도구 파일이 포함된 루트 디렉토리 경로 (str).

    Returns:
        List[str]: 찾은 모든 .py 파일의 절대 경로 리스트.
    """
    tool_files = []

    # 1. tool_directory가 유효한지 확인
    if not os.path.isdir(tool_directory):
        print(f"오류: 디렉토리 '{tool_directory}'를 찾을 수 없거나 유효하지 않습니다.")
        return tool_files

    # 2. os.walk를 사용하여 재귀적으로 탐색
    for root, dirs, files in os.walk(tool_directory):

        # 3. .py 확장자를 가진 파일만 필터링
        for file in files:
            if file.endswith('.py'):
                # __init__.py 파일은 일반적으로 모듈을 정의하는 용도이므로 제외할 수 있지만,
                # 명시적으로 도구가 포함되어 있다면 포함해도 무방합니다. 여기서는 일단 포함합니다.

                # 파일의 전체 경로를 생성하여 리스트에 추가
                full_path = os.path.join(root, file)
                tool_files.append(full_path)

        # (선택 사항) 가상 환경(venv)이나 숨겨진 디렉토리는 탐색에서 제외하여 성능을 개선할 수 있습니다.
        # if '.venv' in dirs:
        #     dirs.remove('.venv')

    return tool_files

# async def main():
#     TOOL_PATH = 'tools/server.py'
#
#     cl = Client(TOOL_PATH)
#     async with cl:
#         ress = await calls(cl, [{'tool_name': 'add',
#                                  'tool_args': {"a": 5, "b": 6}}])
#
#         # 1. 'add' 함수 호출 (가장 간결한 형태)
#         result_add = await _call(
#             cl,
#             "add",
#             {"a": 5, "b": 6}
#         )
#
#         print("\n--- 최종 반환 결과 ---")
#         print(f"add(5, 6)의 결과 (Value): {result_add}")
#
#         result_greet = await _call(
#             cl,
#             "greet",
#             {"name": "Developer"}
#         )
#         print(f"greet('Developer')의 결과 (Value): {result_greet}")

async def load_tools_spec(tools_path: List | None):  # ['calc', 'greet']
    """Load OpenAI-style tool specs from MCP servers for LLM attach context.

    Args:
        tools_path: Tool route ids (e.g. ``['kis/stock']``). Empty/None → ``[]``.

    Returns:
        List of JSON strings, one per tool path, each containing tool metadata.
    """
    tools_spec = []
    max_attempts = 3
    for path in tools_path or []:
        last_err: Exception | None = None
        ress = None
        for attempt in range(max_attempts):
            try:
                tool_path = get_transport_path(path)
                cl = create_mcp_client(tool_path)
                async with cl:
                    ress = tool_specs_for_llm(await cl.list_tools())
                break
            except Exception as e:
                last_err = e
                if attempt + 1 < max_attempts:
                    await asyncio.sleep(0.5)
        if ress is None:
            detail = format_exception(
                last_err,
                context=f"load_tools_spec 실패 [{path}] (attempts={max_attempts})",
            )
            raise RuntimeError(detail) from last_err
        for res in ress:
            res['tool_path'] = f'{path}'
        tools_spec.append(json.dumps(ress, indent=2, ensure_ascii=False))
    return tools_spec if tools_spec else []

# def get_transport_path(path, **kwargs):
#     transport = kwargs.get('transport', 'stdio')  # fastmcp transport style
#     if transport == 'stdio':
#         scan_dirs = [cfg.dump_path, cfg.tools_path]
#         for dir in scan_dirs:
#             full_path = os.path.join(dir, path + '.py')
#             if os.path.exists(full_path):
#                 return full_path
#         raise ValueError(f'fails to find client: {path}')
#     elif transport == 'http':
#         host_port = f'http://{cfg.host}:{cfg.port}'
#         return f'{host_port}/{cfg.mcp_path}/{path}/'
#         # return f'{host_port}/{path}'
#     else:
#         raise ValueError(f'unknown transport: {transport}')

def get_transport_path(path, **kwargs):
    """
    논리적 도구 경로(path)를 바탕으로
    운영체제에 맞는 물리 파일 경로 또는 HTTP 엔드포인트를 반환합니다.
    """

    def check_assets() -> str:
        """assetized → HTTP(8091), 그 외 → tools/{path}/main.py stdio."""
        route = path.lstrip("/").replace("\\", "/")
        if is_assetized(route):
            return "http"
        return "studio"

    # 1. 입력된 경로의 슬래시를 운영체제 표준 구분자로 통일
    normalized_path = path.lstrip("/").replace("/", os.sep)

    transport = kwargs.get("transport", "auto")

    if transport == "auto":
        transport = check_assets()

    if transport in ("stdio", "studio"):
        # stdio: FastMCP 가 서브프로세스로 main.py 실행
        from sage.config import resolve_narratix_home

        tools_root = resolve_narratix_home() / "tools"
        full_path = os.path.normpath(os.path.join(tools_root, normalized_path, "main.py"))

        if os.path.exists(full_path):
            return full_path

        raise ValueError(f"클라이언트를 찾을 수 없습니다: {path} (검색 경로: {tools_root})")

    elif transport == 'http':
        # HTTP: MCP 게이트웨이 — SAGE_MCP_BASE_URL (Docker worker) 또는 cfg.host:8091
        url_path = path.replace(os.sep, '/')
        override = (
            os.environ.get("SAGE_MCP_BASE_URL", "").strip().rstrip("/")
            or cfg.sage_mcp_base_url
        )
        host_port = override if override else f'http://{cfg.host}:{cfg.port + 1}'

        return f'{host_port}/{url_path}/'

    else:
        raise ValueError(f'지원하지 않는 전송 방식(transport)입니다: {transport}')

# 도구들이 위치한 물리적 경로
TOOL_BASE_PATH = cfg.tools_path

# route_path → Lock. ensure_mcp_mounted 가 동시에 같은 도구를 이중 mount 하지
# 않도록 (첫 요청 폭주 / warmup 병렬) per-route 직렬화.
_mount_locks: dict[str, asyncio.Lock] = {}


def _mount_path_for(route_path: str) -> str:
    """FastAPI mount path — trailing slash 고정 (하위 MCP http_app path='/')."""
    normalized = route_path.strip("/").replace("\\", "/")
    return f"/{normalized}/"


def _mounted_routes(app: FastAPI) -> set[str]:
    """app.state.mounted_routes lazy 초기화 — mount 여부 빠른 조회 캐시."""
    mounted = getattr(app.state, "mounted_routes", None)
    if mounted is None:
        app.state.mounted_routes = set()
        mounted = app.state.mounted_routes
    return mounted


def is_route_mounted(app: FastAPI, route_path: str) -> bool:
    """캐시 miss 시 app.routes 를 훑어 trailing-slash 변형까지 동기화."""
    normalized = route_path.strip("/").replace("\\", "/")
    if not normalized:
        return False
    if normalized in _mounted_routes(app):
        return True
    mount_path = _mount_path_for(normalized)
    for route in app.routes:
        if getattr(route, "path", None) in (mount_path, mount_path.rstrip("/")):
            _mounted_routes(app).add(normalized)
            return True
    return False


def route_path_from_url(path: str) -> str | None:
    """assetized 도구 URL 에 대해서만 route_path 를 반환합니다 (가장 긴 prefix 우선).

    URL ``/kis/stock/tools/list`` 처럼 뒤에 MCP 서브경로가 붙어도
    ``kis/stock`` 이 assetized+main.py 이면 그걸 고른다. 짧은 prefix 부터
    매칭하면 상위 디렉토리 도구에 잘못 mount 시도할 수 있어 longest-first.
    """
    segments = [segment for segment in path.strip("/").split("/") if segment]
    for length in range(len(segments), 0, -1):
        candidate = "/".join(segments[:length])
        if not is_assetized(candidate):
            continue
        if (tool_dir(candidate) / "main.py").is_file():
            return candidate
    return None


def _lazy_mount_candidate(route_path: str) -> bool:
    """lazy mount 대상: metadata.status=assetized 이고 main.py 가 있는 도구.

    assetized 가 아니면 HTTP 게이트웨이에 올리지 않고 stdio Client 경로만 쓴다.
    """
    normalized = route_path.strip("/").replace("\\", "/")
    if not normalized or not is_assetized(normalized):
        return False
    return (tool_dir(normalized) / "main.py").is_file()


def _attach_mcp_mount(app: FastAPI, route_path: str, mcp_app: FastAPI) -> None:
    """mount + mcp_apps/mounted_routes 북키핑. lifespan 진입은 호출측 책임."""
    mount_path = _mount_path_for(route_path)
    app.mount(mount_path, mcp_app)
    app.state.mcp_apps.append(mcp_app)
    _mounted_routes(app).add(route_path)


def mount_mcp_tool_at_startup(app: FastAPI, route_path: str, file_path: str) -> bool:
    """create_app 기동 시 assetized 도구를 mount 합니다 (lifespan 은 unified_lifespan 에서 일괄 처리).

    기동 단계에서는 lifespan_stack 이 아직 없으므로 mount 만 하고,
    ``unified_lifespan`` 이 app.state.mcp_apps 전체를 enter_async_context 한다.
    lazy 경로(ensure_mcp_mounted)와 달리 여기서는 lifespan 을 즉시 시작하지 않음.
    """
    normalized = route_path.strip("/").replace("\\", "/")
    if not _lazy_mount_candidate(normalized):
        return False
    if is_route_mounted(app, normalized):
        return True
    mcp_app = load_mcp_from_path(file_path, normalized)
    if mcp_app is None:
        return False
    _attach_mcp_mount(app, normalized, mcp_app)
    return True


async def ensure_mcp_mounted(app: FastAPI, route_path: str) -> bool:
    """assetize 직후 첫 HTTP 요청 시 assetized 도구만 lazy mount 합니다.

    기동 이후(또는 다른 프로세스에서) tools/{route}/metadata 가 assetized 로
    바뀌면 create_app walk 결과에는 없다. 첫 트래픽이 middleware 를 지날 때
    이 함수가 main.py 를 로드·mount 한다.

    double-check locking: Lock 밖에서 mounted? → Lock 획득 → 다시 mounted? →
    candidate 재확인 → load → attach → lifespan_stack 이 있으면 즉시 lifespan 진입.
    (기동 시 mount 된 앱은 unified_lifespan 이 이미 돌렸지만, lazy mount 는
    서버가 이미 yield 한 뒤이므로 stack 에 늦게 넣어야 'lifespan unsupported' 를 피함.)
    """
    normalized = route_path.strip("/").replace("\\", "/")
    if not _lazy_mount_candidate(normalized):
        return False
    if is_route_mounted(app, normalized):
        return True

    lock = _mount_locks.setdefault(normalized, asyncio.Lock())
    async with lock:
        if is_route_mounted(app, normalized):
            return True
        if not _lazy_mount_candidate(normalized):
            return False

        main_py = tool_dir(normalized) / "main.py"
        if not main_py.is_file():
            return False

        mcp_app = load_mcp_from_path(str(main_py), normalized)
        if mcp_app is None:
            return False

        _attach_mcp_mount(app, normalized, mcp_app)

        stack = getattr(app.state, "lifespan_stack", None)
        if stack is not None:
            await stack.enter_async_context(mcp_app.lifespan(mcp_app))

        info(f"lazy mounted MCP tool at {_mount_path_for(normalized)}")
        return True


async def warmup_mcp_tool(route_path: str, *, max_attempts: int = 3) -> None:
    """assetize 직후 MCP HTTP route 를 미리 mount 하고 list_tools 로 검증합니다.

    assetize API 가 metadata 를 바꾼 직후 호출측이 이 함수를 부르면,
    실제 사용자 요청보다 먼저 HTTP Client → list_tools 를 찔러
    (lazy middleware 가 mount 를 완료하도록) cold-start 지연을 앞당긴다.

    get_transport_path(..., transport="http") 로 게이트웨이 URL 을 강제 —
    stdio 로 워밍업하면 mount 경로를 검증하지 못한다. backoff 는 시도마다
    0.5*(attempt+1).
    """
    normalized = route_path.strip("/").replace("\\", "/")
    if not _lazy_mount_candidate(normalized):
        return

    last_err: Exception | None = None
    for attempt in range(max_attempts):
        try:
            tool_path = get_transport_path(normalized, transport="http")
            cl = create_mcp_client(tool_path)
            async with cl:
                await asyncio.wait_for(cl.list_tools(), timeout=30.0)
            info(f"MCP warmup ok: {normalized}")
            return
        except Exception as e:
            last_err = e
            if attempt + 1 < max_attempts:
                await asyncio.sleep(0.5 * (attempt + 1))

    detail = format_exception(
        last_err,
        context=f"MCP warmup 실패 [{normalized}] (attempts={max_attempts})",
    )
    raise RuntimeError(detail) from last_err


def lazy_mount_middleware_factory(gateway: FastAPI):
    """BaseHTTPMiddleware 대신 pure ASGI — lazy mount 시 lifespan 진입 cancel scope 충돌 방지.

    Starlette BaseHTTPMiddleware 는 내부 Task/cancel scope 때문에, 요청 처리
    중에 ``enter_async_context(mcp_app.lifespan)`` 을 await 하면 anyio 취소
    범위가 꼬이는 사례가 있었다. pure ASGI ``__call__(scope, receive, send)``
    미들웨어는 그 래퍼 없이 ensure_mcp_mounted 를 호출할 수 있다.

    http scope 만 검사하고, route 가 이미 mount 됐으면 pass-through.
    gateway 참조를 클로저/인스턴스에 고정해 nested app 과 분리한다.
    """

    class LazyMountMiddleware:
        def __init__(self, app):
            self.app = app
            self.gateway = gateway

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                route_path = route_path_from_url(scope.get("path", ""))
                if (
                    route_path
                    and _lazy_mount_candidate(route_path)
                    and not is_route_mounted(self.gateway, route_path)
                ):
                    await ensure_mcp_mounted(self.gateway, route_path)
            await self.app(scope, receive, send)

    return LazyMountMiddleware


def load_mcp_from_path(file_path: str, route_path: str):
    """파일에서 FastMCP 인스턴스(``module.mcp``)를 찾아 http_app 으로 변환.

    importlib 로 격리 로드(모듈 id 에 route_path). stateless_http=True —
    게이트웨이가 연결 상태를 붙잡지 않고 요청 단위로 도구를 처리.
    """
    module_id = f"mcp_mod_{route_path.replace('/', '_')}"
    spec = importlib.util.spec_from_file_location(module_id, file_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
        if hasattr(module, 'mcp') and isinstance(module.mcp, FastMCP):
            return module.mcp.http_app(
                transport="streamable-http",
                path="/",

                stateless_http=True,
                json_response=True,
            )

    except Exception as e:
        print(f"Error loading module at {file_path}: {e}")
    return None

@asynccontextmanager
async def unified_lifespan(app: FastAPI):
    """
    메인 앱 실행 시 마운트된 모든 하위 MCP 앱의 lifespan을 함께 실행하여
    'lifespan protocol unsupported' 오류를 방지합니다.

    FastAPI 하위 mount 앱은 부모 lifespan 과 자동 연동되지 않으므로
    AsyncExitStack 으로 일괄 enter. ``app.state.lifespan_stack`` 을 노출해
    lazy mount(ensure_mcp_mounted)가 나중에 같은 stack 에 합류하게 한다.
    ready_queue 가 있으면 부모 프로세스에 'loaded N tools…' 핸드셰이크.
    """
    async with AsyncExitStack() as stack:
        app.state.lifespan_stack = stack
        _mounted_routes(app)
        for mcp_app in getattr(app.state, "mcp_apps", []):
            # 하위 MCP 앱의 초기화 로직(DB 연결 등) 실행
            await stack.enter_async_context(mcp_app.lifespan(mcp_app))
        ready_queue = getattr(app.state, "ready_queue", None)
        if ready_queue is not None:
            host = getattr(app.state, "mcp_host", cfg.host)
            port = getattr(app.state, "mcp_port", cfg.port + 1)
            ready_queue.put(mcp_loaded_message(app, host, port))
        yield

def mcp_loaded_message(app: FastAPI, host: str, port: int) -> str:
    n = len(getattr(app.state, "mcp_apps", []))
    return (
        f"loaded {n} tools from {TOOL_BASE_PATH} on http://{host}:{port}"
    )

def create_app(*, host: str | None = None, port: int | None = None) -> FastAPI:
    """Build the hierarchical MCP gateway that mounts assetized tool ``main.py`` apps.

    Args:
        host: Bind host (defaults to ``cfg.host``).
        port: Bind port (defaults to ``cfg.port + 1``).

    Returns:
        FastAPI app with lazy-mount middleware and unified lifespan.

    mount 로직
    ----------
    1. tools/ 트리를 walk 하며 ``main.py`` + ``is_assetized(route)`` 인 디렉토리만
       ``mount_mcp_tool_at_startup`` (stdio 전용·미 assetize 도구는 건너뜀 —
       Client 가 서브프로세스로 직접 뜸).
    2. ``unified_lifespan`` 을 루트 lifespan 으로 걸어 하위 mcp_apps lifespan 통합.
    3. ``lazy_mount_middleware_factory`` 를 맨 마지막에 추가 — 기동 이후
       assetize 된 도구의 첫 HTTP 요청에서 ensure_mcp_mounted.
    포트는 보통 ``cfg.port + 1`` (API 서버와 MCP 게이트웨이 분리).
    """
    bind_host = host or cfg.host
    bind_port = port if port is not None else cfg.port + 1

    root_app = FastAPI(
        title="Hierarchical MCP Gateway",
        lifespan=unified_lifespan
    )
    root_app.state.mcp_apps = []
    root_app.state.mounted_routes = set()
    root_app.state.mcp_host = bind_host
    root_app.state.mcp_port = bind_port

    # tools 폴더 — metadata.status=assetized 인 main.py 만 MCP HTTP 로 노출
    for root, dirs, files in os.walk(TOOL_BASE_PATH):
        if "main.py" not in files:
            continue

        rel_path = os.path.relpath(root, TOOL_BASE_PATH)
        if rel_path == ".":
            continue
        route_path = rel_path.replace(os.sep, "/")

        if not is_assetized(route_path):
            continue

        file_path = os.path.join(root, "main.py")
        mount_mcp_tool_at_startup(root_app, route_path, file_path)
    info(mcp_loaded_message(root_app, bind_host, bind_port))

    @root_app.get("/")
    async def index():
        return {
            "service": "MCP Gateway",
            "endpoints": [
                getattr(route, "path", str(route)) for route in root_app.routes
            ],
        }

    root_app.add_middleware(lazy_mount_middleware_factory(root_app))

    return root_app

if __name__ == "__main__":
    import asyncio

    print(asyncio.run(load_tools_spec(["calc", "greet"])))
