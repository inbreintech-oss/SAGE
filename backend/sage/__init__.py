import importlib.util
import json
import logging
import os
import sys
from contextlib import asynccontextmanager, AsyncExitStack
from typing import Dict, Any, List

import yaml
from starlette.applications import Starlette
from starlette.routing import Mount

import cfg
# sage.data 는 필요 시점에 import (exec worker·MCP client 경량 기동)

# --- 초기 설정 ---
logging.basicConfig(level=logging.WARNING)
TOOL_PATH = os.environ.get("TOOL_PATH", "tools")

# -----------------
# async def load_meta_data(app: Starlette):
#     """서버 시작 시 meta.yml 파일을 한 번만 읽어 앱 상태에 저장합니다."""
#     metadata_file_path = os.path.join(cfg.rscs_path, 'meta.yml')
#
#     # 캐시할 전역 변수 초기화
#     app.state.data_info = {}
#
#     try:
#         with open(metadata_file_path, 'r', encoding='utf-8') as f:
#             data_info = yaml.safe_load(f) or {}
#             app.state.data_info = data_info  # 메모리에 저장
#             # print('메타 데이터 로드 완료 (meta.yml)')
#     except FileNotFoundError:
#         print(f"Warning: Metadata file not found at {metadata_file_path}")
#     except Exception as e:
#         print(f"데이터 메타 로드 중 오류 발생: {e}")

async def load_meta_data(app: Starlette):
    """
    Redis로부터 모든 통합 스키마 (schema:{did}) Hash를 읽어와 앱 상태에 저장합니다.

    저장 구조 예시:
    app.state.data_info = {
        'drug': {
            'schema': { ... Pydantic JSON Schema Dict ... },
            'meta': { ... DatasetInfo Meta Dict ... }
        },
        'food': { ... }
    }
    """

    # 캐시할 전역 변수 초기화
    app.state.data_info: Dict[str, Dict[str, Any]] = {}

    try:
        r = sage.data.redis.client()

        # ----------------------------------------------------
        # --- 1. 모든 'schema:*' 키 검색 및 일괄 로드 ---
        # ----------------------------------------------------
        # 'schema:*' 패턴으로 모든 스키마 키를 비동기적으로 검색
        #
        schema_keys: List[str] = [key async for key in r.scan_iter("schema:*")]

        if not schema_keys:
            print("⚠️ Redis에서 'schema:*' 패턴의 키를 찾을 수 없습니다. 데이터셋 정보가 비어 있습니다.")
            return

        # Pipeline을 사용하여 Hash 전체 (HGETALL) 일괄 로드
        pipe = r.pipeline()
        for key in schema_keys:
            pipe.hgetall(key)

        unified_data_list = await pipe.execute()

        # ----------------------------------------------------
        # --- 2. 데이터 분리 및 복원 (역직렬화) ---
        # ----------------------------------------------------

        for key, unified_data in zip(schema_keys, unified_data_list):
            if not unified_data:
                continue

            # 🟢 2-1. DID (Dataset ID) 추출 (수정)
            # 'schema:drug' -> 'drug'
            try:
                did = key.split(':', 1)[1]
            except IndexError:
                print(f"❌ 잘못된 Redis 키 형식 건너뜀: {key}")
                continue

            # 2-2. JSON Schema 복원 ('schema' 필드)
            schema_json_str = unified_data.pop('schema', None)

            if schema_json_str:
                try:
                    schema_dict = json.loads(schema_json_str)
                except json.JSONDecodeError:
                    print(f"❌ {did} 스키마 JSON 디코딩 실패. 데이터셋 로드에서 제외합니다.")
                    continue
            else:
                print(f"⚠️ {did} 데이터셋의 'schema' 필드가 누락되었습니다. 메타데이터만 로드합니다.")
                schema_dict = {}

            # 2-3. 메타데이터 복원 (나머지 필드)
            # unified_data에는 'schema'를 제외한 모든 메타데이터가 남아 있습니다.
            meta_data = unified_data

            # 🟢 모든 JSON 직렬화된 복합 객체(List/Dict) 복원
            for field_name, value in meta_data.items():
                if isinstance(value, str):
                    try:
                        # 디코딩 시도
                        decoded_value = json.loads(value)

                        # 디코딩된 값이 List 또는 Dict이면 원래 객체로 대체합니다.
                        if isinstance(decoded_value, (list, dict)):
                            meta_data[field_name] = decoded_value

                    except json.JSONDecodeError:
                        # 일반 문자열은 그대로 유지합니다.
                        pass

            # 2-4. 앱 상태에 최종 저장
            app.state.data_info[did] = {
                'schema': schema_dict,
                **meta_data
            }

        print(f"⭐ 최종적으로 {len(app.state.data_info)}개 데이터셋의 스키마 및 메타 정보 로드 완료.")

    except Exception as e:
        print(f"🚨 Redis 스키마/메타데이터 로드 중 오류 발생: {e}")

async def load_report_executable(app: Starlette):
    """서버 시작시 report 등 실행 정보 로드"""
    file_path = os.path.join(cfg.rscs_path, 'tooled.yml')

    # 캐시할 전역 변수 초기화
    app.state.sage_info = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sage_info = yaml.safe_load(f) or {}
            app.state.sage_info = sage_info  # 메모리에 저장
    except FileNotFoundError:
        print(f"Warning: SAG-E file not found at {file_path}")
    except Exception as e:
        print(f"데이터 메타 로드 중 오류 발생: {e}")

# async def attach_routes_tools_path(app: Starlette,
#                                    tools_path: str = TOOL_PATH,
#                                    routes_path='/mcp',  # 💡 기본 경로를 '/mcp'로 가정
#                                    ) -> Starlette:
#     """
#         tools_path 내의 모든 .py 파일을 스캔하여
#         attach_routes_with_tools를 통해 동적으로 마운트합니다.
#         """
#     print(f"\nScanning directory: '{tools_path}' for MCP tools...")
#
#     if not hasattr(app.state, 'mcp_apps'):
#         app.state.mcp_apps = []
#
#     for filename in os.listdir(tools_path):
#         if filename.endswith(".py") and filename != "__init__.py":
#             tool_name = filename[:-3]
#
#             # 개별 등록 로직 호출
#             await attach_routes_with_tool(app, tool_name, routes_path)
#
#     return app

async def attach_routes_tools_path(app: Starlette,
                                   tools_path: str = TOOL_PATH,
                                   routes_path: str = '/mcp') -> Starlette:
    """
    tools_path 내의 모든 하위 폴더를 탐색하여
    계층 경로(예: 'data/load')를 추출하고 마운트 함수를 호출합니다.
    """
    if not hasattr(app.state, 'mcp_apps'):
        app.state.mcp_apps = []

    for root, dirs, files in os.walk(tools_path):
        for filename in files:
            if filename.endswith(".py") and filename != "__init__.py":
                # 예. data\\load.py  -> data/load
                rel_file_path = os.path.relpath(os.path.join(root, filename), tools_path)
                tool_path = os.path.splitext(rel_file_path)[0].replace(os.sep, '/')

                await attach_routes_with_tool(app, tool_path, routes_path)

    return app

# async def attach_routes_with_tool(app: Starlette,
#                                   tool_name: str,
#                                   routes_path: str = '/mcp') -> Starlette:
#     """
#     단일 MCP 모듈 파일을 로드하여 Starlette 앱에 마운트합니다.
#     실시간으로 특정 도구 하나만 추가하고 싶을 때도 이 함수를 호출하면 됩니다.
#     """
#     try:
#         file_path = os.path.join(TOOL_PATH, tool_name + '.py')
#
#         if tool_name in sys.modules:
#             del sys.modules[tool_name]
#
#         spec = importlib.util.spec_from_file_location(tool_name, file_path)
#         tool_module = importlib.util.module_from_spec(spec)
#         spec.loader.exec_module(tool_module)
#
#         if hasattr(tool_module, 'mcp') and isinstance(getattr(tool_module, 'mcp'), FastMCP):
#             mcp_instance = getattr(tool_module, 'mcp')
#
#             # Tool 엔드포인트 설정
#             mcp_app = mcp_instance.http_app(path='/', transport='streamable-http')
#
#             # 중복 등록 방지를 위해 state 확인 (필요 시)
#             if not hasattr(app.state, 'mcp_apps'):
#                 app.state.mcp_apps = []
#
#             app.state.mcp_apps.append(mcp_app)
#
#             # 경로 설정 및 마운트
#             path = f'{routes_path}/{tool_name}/'
#             # app.routes.append(Mount(path=path, app=mcp_app))
#
#             for route in app.routes[:]:  # 복사본으로 순회
#                 if isinstance(route, Mount) and route.path == path:
#                     app.routes.remove(route)
#
#                 # 새로운 경로 추가
#             app.routes.append(Mount(path=path, app=mcp_app))
#
#             if hasattr(app.state, 'stack'):
#                 await app.state.stack.enter_async_context(mcp_app.lifespan(mcp_app))
#
#             print(f"Successfully mounted Tool '{tool_name}' -> URL: {path}")
#
#     except Exception as e:
#         print(f"Error loading tool from {tool_name}. Details: {e}")
#
#     return app

async def attach_routes_with_tool(app: Starlette,
                                  tool_path: str,
                                  routes_path: str = '/mcp') -> Starlette:
    """
    tool_path(예: 'data/load' 또는 'market_viewer')를 받아
    해당 경로의 MCP 모듈을 Starlette 앱에 마운트합니다.
    """
    try:
        # 1. 실제 물리 파일 경로 구성
        # tool_path가 'data/load'라면 TOOL_PATH/data/load.py 가 됨
        file_path = os.path.join(TOOL_PATH, f"{tool_path}.py")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Tool file not found at: {file_path}")

        # 2. 모듈 식별자 구성 (점 표기법: data.load)
        module_id = tool_path.replace('/', '.')

        # 모듈 캐시 초기화 (실시간 반영)
        if module_id in sys.modules:
            del sys.modules[module_id]

        # 3. 모듈 동적 로드
        spec = importlib.util.spec_from_file_location(module_id, file_path)
        tool_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool_module)

        # 4. MCP 인스턴스 확인 및 Starlette 앱 추출
        if hasattr(tool_module, 'mcp'):
            mcp_instance = getattr(tool_module, 'mcp')
            mcp_app = mcp_instance.http_app(path='/', transport='streamable-http')

            if not hasattr(app.state, 'mcp_apps'):
                app.state.mcp_apps = []
            app.state.mcp_apps.append(mcp_app)

            # 5. 엔드포인트 경로 설정 (예: /mcp/data/load/)
            # 제시하신 f'{routes_path}/<path-in-tools>/{tool_name}/' 규칙 적용
            mount_path = f"{routes_path}/{tool_path}/"
            # if not mount_path.endswith('/'):
            #     mount_path += '/'

            # 중복 마운트 제거 로직
            for route in app.routes[:]:
                if isinstance(route, Mount) and route.path == mount_path:
                    app.routes.remove(route)

            # 6. 마운트 실행
            app.routes.append(Mount(path=mount_path, app=mcp_app))

            # 7. Lifespan 관리 (비동기 컨텍스트 진입)
            if hasattr(app.state, 'stack'):
                await app.state.stack.enter_async_context(mcp_app.lifespan(mcp_app))

            print(f"Successfully mounted -> path: {mount_path}")

    except Exception as e:
        print(f"Error loading tool from path '{tool_path}': {e}")

    return app

@asynccontextmanager
async def combined_lifespan(app: Starlette):
    """
    마운트된 하위 FastMCP 애플리케이션의 lifespan context를 통합하여 관리합니다.
    """
    await load_meta_data(app)
    await load_report_executable(app)

    # await attach_routes_tools_path(app)

    async with AsyncExitStack() as stack:
        # [추가 1] 나중에 새 도구를 담기 위해 스택을 state에 저장
        app.state.stack = stack

        await attach_routes_tools_path(app)

        # # app.state에서 저장된 FastMCP 앱 리스트를 가져와 사용
        # mounted_apps = getattr(app.state, 'mcp_apps', [])
        #
        # try:
        #     for sub_app in mounted_apps:
        #         await stack.enter_async_context(sub_app.lifespan(sub_app))
        #
        # except AttributeError as e:
        #     sys.stderr.write(f"[Lifespan CRITICAL ERROR] FastMCP 세션 시작 실패: {e}. Starlette 다중 마운팅 불가.\n")
        #     sys.exit(1)
        # print(f"Server started and tools initialized.")
        yield

# if __name__ == "__main__":
#     # 기본 Starlette 앱 생성 (이 시점에는 라우트가 없음)
#     app = Starlette(lifespan=combined_lifespan)
#
#     # 루트 라우트 (/i)를 먼저 추가
#     app.routes.append(Mount(path='/i', app=FastAPI()))
#
#     # ⭐ attach_routes_with_mcp_tools를 파이프라인처럼 호출하여 라우트 설정 완료된 앱을 받음
#     app = attach_routes_with_tools(app)
#
#     uvicorn.run(
#         app,
#         host=os.environ.get("HOST", "127.0.0.1"),
#         port=int(os.environ.get("PORT", 8090)),
#         log_level='error'
#     )
