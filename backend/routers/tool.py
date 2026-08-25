"""MCP tool API — generate, update, exec, assetize, and recommend tools."""

import ast
import asyncio
import json
import shutil
import traceback
from pathlib import Path
from typing import Any, List, Optional, Dict

from fastapi import APIRouter, HTTPException, Depends, Query
from sse_starlette import EventSourceResponse
from pydantic import BaseModel, Field, ConfigDict, ValidationError

import cfg
from sage import nodes
from sage import tool as tools
from sage.config import TOOLS_DIR
from sage.db import saged, SAGEDataStore, get_db
from sage.errs import format_exception
from sage.logg import error, LoggingRoute, debug
from sage.models import doc
from sage.models.doc import ToolStatus, Tool

from routers.base import SSEEncoder, DeleteResponse, APIResponse
from sage.models.tool import ToolExecResult
from sage.models.req import (
    ToolGenerateRequest,
    ToolUpdateRequest,
    ToolListRequest,
    AssetizeRequest,
    AssetizeResponse,
    ToolDeleteRequest,
    ToolRecommendRequest,
    ToolRecommendResponse,
)
from sage.models.tool import ToolPack, ToolGenerateInput
from sage.tool import execute_with_fix, execute_caller_with_fix
from sage.tool.assetize import perform_assetize
from sage.tool.metadata import is_assetized
from sage import prompt as pp
from sage.llm import GeminiLLM
from sage.mcp import load_tools_spec
from sage.report.runner import TaskReporter

router = APIRouter(
    prefix="/tool",  # 공통 경로 접두어
    tags=["tool"],  # Swagger 문서상의 그룹 이름
    route_class=LoggingRoute
)


def _save_query_examples(tool_id: str, examples: list[str]) -> None:
    meta_path = TOOLS_DIR / tool_id / "metadata.json"
    if not meta_path.is_file():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["query_examples"] = examples
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


@router.post("/generate")
async def generate_tool(
        req: ToolGenerateRequest
):
    """도구 생성 프로세스 시작 (EventSourceResponse 반환)"""
    return EventSourceResponse(
        handle_tool_generation(req, saged)
    )


@router.patch("/update")
async def update_tool(
        req: ToolUpdateRequest  # 업데이트를 위한 요청 스키마 (tool_id 포함)
):
    """도구 업데이트 프로세스 시작 (EventSourceResponse 반환)"""
    return EventSourceResponse(
        handle_tool_update(req, saged)
    )


class ToolExecRequest(BaseModel):
    query: str = Field(description="사용자의 자연어 질의")
    tools: List[str] = Field(description="사용 가능한 도구 ID 목록 (콤마 구분)")
    return_type: str = Field("full", description="[result] only or [full]")

    model_config = ConfigDict(from_attributes=True,
                              json_schema_extra={
                                  "example": {
                                      "query": "사용자 질의",
                                      "tools": ["도구 식별자"]
                                  }
                              }
                              )


@router.post("/exec")
async def exec_tool(req: ToolExecRequest) -> APIResponse[Any]:
    """
    사용자 질의를 LLM으로 분석하여 도구를 실행하는 API
    """
    # ------------------------------------------------------------------
    # exec 플로우: 질의 → tool/executor(caller codegen) → smoke 실행
    # - generate/update 와 달리 도구를 "만들고" 저장하지 않음.
    # - 사용자가 고른 tools[] 범위 안에서만 caller를 짜게 해 탈선 방지.
    # ------------------------------------------------------------------
    if not req.tools:
        return APIResponse(success=False, error="사용 가능한 도구 목록이 비어 있습니다.")

    try:
        # LLM이 질의를 해석해 호출 코드(caller)를 생성
        executor = nodes.nodes['tool/executor']
        tool_res: ToolExecResult = await executor.run(
            query=req.query,
            tools=req.tools
        )

        debug(f'도구 caller 생성 완료...{tool_res.model_dump()}')
        # Auto-fix 래퍼로 1회 실행 — 단순 SyntaxError 등은 내부에서 보정 시도.
        res, _ = await execute_caller_with_fix(tool_res.caller)

        # 'result' from fastmcp call itself. eliminate it.
        payload = res.get("result", res) if isinstance(res, dict) else res
        return APIResponse(success=True, result=payload)

    except Exception as e:
        return APIResponse(
            success=False,
            error=f"도구 실행 중 오류 발생:\n{format_exception(e)}",
        )


def _tool_list_params(
        status: doc.ToolStatus | None = Query(default=None, description="None=전체 도구"),
) -> ToolListRequest:
    return ToolListRequest(status=status)


@router.post("/list/query", response_model=APIResponse[List[doc.Tool]])
async def list_tools_query(req: ToolListRequest, db: SAGEDataStore = Depends(get_db)):
    """
    도구 목록 조건 필터 조회.
    status, provider, category, tags 조건을 동적으로 결합하여 필터링합니다.
    """
    try:
        col = db.get_collection(doc.Tool)

        # 동적 쿼리 빌딩
        query = {}

        if req.status:
            query["status"] = {"$in": req.status}
        if req.secret_id:
            query["secret_id"] = req.secret_id
        if req.category:
            query["category"] = req.category
        if req.tags:
            query["tags"] = {"$all": req.tags}

        cursor = col.find(query)

        tool_list = []
        async for cur in cursor:
            try:
                tool_list.append(Tool.model_validate(cur))
            except ValidationError:
                continue

        return APIResponse[List[doc.Tool]](success=True, result=tool_list)

    except Exception as e:
        return APIResponse[List[doc.Tool]](
            success=False,
            error=f"도구 목록을 필터링하는 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/list", response_model=APIResponse[List[doc.Tool]])
async def list_tools(db: SAGEDataStore = Depends(get_db)):
    """
    전체 도구 목록 조회.
    """
    # 쿼리 조건이 전혀 없는 기본 Request 객체 생성
    empty_req = ToolListRequest()

    # 동일한 db 컨텍스트를 주입하며 필터 API 함수로 로직을 위임
    return await list_tools_query(req=empty_req, db=db)


# 상세 데이터 스키마
class ToolInput(BaseModel):
    name: str
    type: str
    description: Optional[str] = None


class ToolFunction(BaseModel):
    name: str
    description: Optional[str] = None
    inputs: List[ToolInput]
    outputs: List[Dict[str, Any]]


class ToolInfoDetail(Tool):
    # tool_id: str
    # title: str
    # description: str | None = None
    funcs: List[Dict[str, Any]] | None = None
    # code: str | None = None
    # caller: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def extract_funcs_from_code(code: str) -> List[Dict[str, Any]]:
    """
    Python AST를 사용하여 MCP 도구 및 Pydantic 모델을 계층적 구조로 분석합니다.
    """
    # ------------------------------------------------------------------
    # AST 목적
    # - /tool/info UI 는 실행 없이 "이 도구가 어떤 입·출력을 갖는지"를
    #   보여줘야 한다. exec/import 하면 side-effect·비밀키가 위험하므로
    #   소스 텍스트만 파싱한다.
    # - MCP 노출면은 `@mcp.tool` / `@xxx.tool` 데코레이터가 붙은 함수만
    #   해당 — 헬퍼 함수는 UI 목록에서 제외.
    # - 인자·반환이 Pydantic 모델이면 class_map 으로 중첩 properties 를
    #   펼쳐 FE 가 JSON Schema 비슷한 폼을 그릴 수 있게 한다.
    # - simplify_dtype: TS/JSON 친화 타입(string/number/…)로 정규화.
    # ------------------------------------------------------------------
    try:
        tree = ast.parse(code)
    except Exception:
        # 구문 오류 도구도 info API 가 500 이 되지 않게 빈 funcs.
        return []

    # 1. 타입 단순화 매핑 함수
    def simplify_dtype(raw_type: str) -> str:
        raw_type = raw_type.strip()
        # 제너릭 제거 및 소문자화
        if "List" in raw_type: return "list"
        if "Dict" in raw_type or "Any" in raw_type: return "dict"

        mapping = {
            "str": "string",
            "int": "number",
            "float": "number",
            "bool": "boolean",
            "datetime": "string",
            "Optional[str]": "string",
            "Optional[int]": "number",
            "Optional[float]": "number"
        }
        return mapping.get(raw_type, raw_type)

    # 2. 클래스 정의(Pydantic 모델) 사전 수집 — 함수 walk 전에 맵을 채움.
    #    AnnAssign + Field(description=...) 만 추출; 메서드 바디는 무시.
    class_map = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            props = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    f_name = item.target.id
                    f_raw_type = ast.unparse(item.annotation)
                    f_desc = ""

                    # Field description 추출
                    if isinstance(item.value, ast.Call) and getattr(item.value.func, 'id', '') == 'Field':
                        for kw in item.value.keywords:
                            if kw.arg == 'description' and isinstance(kw.value, ast.Constant):
                                f_desc = kw.value.value

                    props.append({
                        "name": f_name,
                        "dtype": simplify_dtype(f_raw_type),
                        "raw_type": f_raw_type,  # 클래스 추적용 원본 보관
                        "description": f_desc
                    })
            class_map[node.name] = props

    def resolve_properties(raw_type: str) -> Optional[List[Dict[str, Any]]]:
        """클래스 이름을 찾아 내부 properties를 재귀적으로 반환합니다."""
        # Optional[FXResult] / List[FXResult] → FXResult 이름만 추출
        base_class = raw_type.replace("Optional[", "").replace("List[", "").replace("]", "").strip()

        if base_class in class_map:
            results = []
            for p in class_map[base_class]:
                p_new = {
                    "name": p["name"],
                    "dtype": p["dtype"],
                    "description": p["description"]
                }
                # nested 모델이면 properties 중첩 — FE 트리 폼용.
                nested_props = resolve_properties(p["raw_type"])
                if nested_props:
                    p_new["properties"] = nested_props
                results.append(p_new)
            return results
        return None

    found_funcs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            # decorator_list 에 .tool 속성/호출이 있어야 MCP 공개 함수.
            is_mcp_tool = any(
                (isinstance(d, ast.Call) and getattr(d.func, 'attr', '') == 'tool') or
                (isinstance(d, ast.Attribute) and d.attr == 'tool')
                for d in node.decorator_list
            )

            if is_mcp_tool:
                # 3. Inputs 분석
                inputs = []
                for arg in node.args.args:
                    if arg.arg in ("self", "cls"): continue
                    raw_in_type = ast.unparse(arg.annotation) if arg.annotation else "Any"
                    in_info = {
                        "name": arg.arg,
                        "dtype": simplify_dtype(raw_in_type),
                        "description": None,
                        "properties": resolve_properties(raw_in_type)
                    }
                    inputs.append(in_info)

                # 4. Outputs — 반환 타입 annotation + docstring 을 description 으로.
                outputs = []
                if node.returns:
                    raw_out_type = ast.unparse(node.returns)
                    out_info = {
                        "dtype": simplify_dtype(raw_out_type),
                        "description": ast.get_docstring(node) or "",
                        "properties": resolve_properties(raw_out_type)
                    }
                    outputs.append(out_info)

                found_funcs.append({
                    "name": node.name,
                    "description": ast.get_docstring(node),
                    "inputs": inputs,
                    "outputs": outputs
                })

    return found_funcs


@router.get("/info", response_model=APIResponse[ToolInfoDetail])
async def info_tool(tool_id: str, db: SAGEDataStore = Depends(get_db)):
    """
    특정 도구의 상세 정보와 코드 분석 결과를 공통 응답 규격에 맞춰 반환합니다.
    """
    try:
        # 1. DB에서 도구 로드
        col = db.get_collection(doc.Tool)
        tool = await col.find_one({'tool_id': tool_id})

        if not tool:
            return APIResponse[ToolInfoDetail](
                success=False,
                error="해당 도구를 찾을 수 없습니다.",
                result=None
            )

        # 2. 코드 분석
        analyzed_funcs = extract_funcs_from_code(tool['code'])

        # 3. 데이터 구성
        detail = ToolInfoDetail(
            tool_id=tool['tool_id'],
            title=tool['title'],
            description=tool.get('description'),
            query=tool.get('query'),
            funcs=analyzed_funcs,
            code=tool.get('code'),
            caller=tool.get('caller'),
            category=tool.get('category'),
            tags=tool.get('tags'),
            secret_id=tool.get('secret_id'),
            status=tool.get('status'),
            query_examples=tool.get('query_examples'),
            created_at=str(tool['created_at']) if 'created_at' in tool else None,
            updated_at=str(tool['updated_at']) if 'updated_at' in tool else None
        )

        return APIResponse[ToolInfoDetail](
            success=True,
            result=detail
        )

    except Exception as e:
        return APIResponse[ToolInfoDetail](
            success=False,
            error=str(e),
            result=None
        )


@router.post("/recommend", response_model=APIResponse[ToolRecommendResponse])
async def recommend_tools(req: ToolRecommendRequest, db: SAGEDataStore = Depends(get_db)):
    """
    데이터셋 스키마와 지정 카테고리의 assetized 도구를 분석하여
    통합 데이터 분석·갱신에 적합한 도구 path 를 추천합니다.
    """
    # ------------------------------------------------------------------
    # recommend 플로우
    # - 후보를 assetized + category 로 먼저 DB 필터 (generated 초안 제외).
    # - 스키마 + MCP spec + 요약을 LLM 에 넣고 path 만 JSON 으로 받음.
    # - 응답은 allowed 집합으로 재필터 — 환각 path 가 FE 로 새지 않게.
    # ------------------------------------------------------------------
    try:
        data_doc = await db.get(req.did)
        if not data_doc:
            return APIResponse(success=False, error=f"데이터셋을 찾을 수 없습니다: {req.did}")

        schema_info = await pp.load_schema(req.did)

        tool_col = db.get_collection(doc.Tool)
        # 운영에 올린(assetized) 도구만 — 생성 중 generated 는 추천 제외.
        cursor = tool_col.find({"status": "assetized", "category": req.tool_category})

        tool_paths: list[str] = []
        tool_summaries: list[dict[str, str]] = []
        async for item in cursor:
            t_id = item.get("tool_id") or item.get("_id")
            if not t_id:
                continue
            tool_paths.append(str(t_id))
            tool_summaries.append({
                "tool_id": str(t_id),
                "title": item.get("title") or "",
                "description": item.get("description") or "",
            })

        if not tool_paths:
            return APIResponse(
                success=False,
                error=f"카테고리 '{req.tool_category}' 에 해당하는 assetized 도구가 없습니다.",
            )

        # MCP JSON schema 를 추가해 필드 매칭 품질을 높임.
        tools_spec_list = await load_tools_spec(tool_paths)

        prompt = f"""
당신은 데이터 분석 전문가입니다. 아래 데이터셋 스키마와 도구 목록을 보고,
이 데이터셋 분석·갱신·확장에 가장 적합한 도구 path 를 추천하세요.

[데이터셋 이름]: {data_doc.get('name', '알 수 없음')}
[데이터셋 설명]: {data_doc.get('description') or ''}
[데이터 스키마]:
{json.dumps(schema_info, ensure_ascii=False) if isinstance(schema_info, dict) else schema_info}

[카테고리]: {req.tool_category}
[후보 도구 (title/description)]:
{json.dumps(tool_summaries, ensure_ascii=False)}

[도구 MCP spec]:
{json.dumps(tools_spec_list, ensure_ascii=False)}

[출력 형식] JSON 만:
{{
  "recommended_tools": ["tool_path_1", "tool_path_2"]
}}

- recommended_tools 는 위 후보 tool_id/path 만 포함
- 스키마 필드·소스와 연관성이 높은 순으로 1~5개
"""
        raw_response = await GeminiLLM().generate_async(prompt)
        clean_json = raw_response.strip().replace("```json", "").replace("```", "")
        recommendation = json.loads(clean_json)

        recommended = recommendation.get("recommended_tools", [])
        if not isinstance(recommended, list):
            recommended = []

        # 화이트리스트 재필터 — LLM 환각 path 차단.
        allowed = set(tool_paths)
        filtered = [t for t in recommended if t in allowed]

        return APIResponse(
            success=True,
            result=ToolRecommendResponse(recommended_tools=filtered),
        )

    except Exception as e:
        error(f"Tool recommend error: {traceback.format_exc()}")
        return APIResponse(
            success=False,
            error=f"도구 추천 중 오류: {str(e)}",
        )


async def handle_tool_generation(req: ToolGenerateRequest, db: SAGEDataStore):
    """ToolPack 기반 도구 생성 (code LLM + smoke caller + query_examples)."""
    # ==================================================================
    # generate 플로우 (SSE)
    # initializing → generating(코드) → validating(dump+smoke) → completed
    # - status 는 "generated": 아직 운영 경로(assetize)로 올리지 않은 초안.
    # - tools.dump 로 디스크 패키지를 먼저 만들고 smoke 로 검증한 뒤 Mongo.
    # - asyncio.sleep(0): 이벤트 루프에 yield 해 SSE 프레임이 즉시 flush.
    # ==================================================================
    tool_id = 'tm-error-ffffffff'

    yield SSEEncoder.encode("initializing", "도구 생성을 시작합니다.", req=req.model_dump())
    await asyncio.sleep(0)

    try:
        yield SSEEncoder.encode("generating", "도구 소스(code) 생성 중입니다.")
        await asyncio.sleep(0)

        # from_request: secret/참조도구 등 LLM 입력을 정규화.
        gen_input = await ToolGenerateInput.from_request(
            query=req.query,
            tools=req.tools,
            description=req.description,
            ref_code=req.ref_code,
            secret_id=req.secret_id,
            user_id=req.user_id,
        )

        pack: ToolPack = await nodes.nodes["tool/generator"].run(**gen_input.model_dump())

        yield SSEEncoder.encode("validating", "도구 검증 및 smoke 테스트 caller 실행")
        await asyncio.sleep(0)

        tool_status: doc.ToolStatus = "generated"

        # 디스크(tools/{id})에 먼저 기록 — MCP 로더/실행기가 파일을 읽음.
        tools.dump(
            pack, tool_status, instructions=req.query, secret_id=gen_input.secret_id
        )
        _save_query_examples(pack.tool_id, pack.query_examples)

        # smoke caller 실행 — docker_pool + progress tail (report run_task 와 동일)
        reporter = TaskReporter()
        exec_task = asyncio.create_task(execute_with_fix(pack, reporter=reporter))
        async for msg in reporter.iter_while(exec_task):
            yield SSEEncoder.encode("progress", msg)
            await asyncio.sleep(0)
        _, validated_tool = await exec_task
        tool_id = validated_tool.tool_id

        tool_doc = doc.Tool(
            tool_id=validated_tool.tool_id,
            title=validated_tool.title,
            description=validated_tool.description,
            code=validated_tool.code,
            caller=validated_tool.caller,
            query_examples=pack.query_examples,
            status=tool_status,
            category=req.category,
            tags=req.tags,
            query=req.query,
            secret_id=gen_input.secret_id,
        )
        await db.save(tool_doc)

        result = validated_tool.model_dump(mode="json")
        result["query_examples"] = pack.query_examples
        result["status"] = tool_status

        yield SSEEncoder.encode(
            "completed",
            "도구 생성이 완료되었습니다.",
            tool_id=tool_id,
            result=result,
        )

    except Exception as e:
        error(f"도구 생성 오류 [{tool_id}]: {traceback.format_exc()}")
        yield SSEEncoder.encode("failed", f"중단됨: {str(e)}", tool_id=tool_id)


async def handle_tool_update(req: ToolUpdateRequest, db: SAGEDataStore):
    """
    도구 업데이트 핸들러 (SSE 스트리밍)
    """
    # ==================================================================
    # update 플로우
    # - generated 상태만 허용: assetized 운영본을 여기서 덮으면
    #   경로/의존성을 깨뜨릴 수 있어 수정은 초안 단계에서만.
    # - tool/update 노드가 기존 code/caller 를 참고해 패치 후
    #   dump → execute_with_fix → Mongo save (generate 와 대칭).
    # ==================================================================
    tool_id = req.tool_id
    try:
        # 1. 프로세스 시작 알림
        yield SSEEncoder.encode("initializing", "도구 수정을 시작합니다.")

        # 2. 기존 도구 정보 조회 (필요 시)
        existing_tool = await db.load(doc.Tool, tool_id)
        if not existing_tool:
            raise Exception(f"도구를 찾을 수 없습니다: {tool_id}")

        # assetized/기타 상태는 별도 assetize·배포 경로로 다루어야 함.
        if existing_tool.status != "generated":
            raise ValueError(f"생성(generated) 상태의 도구만 수정이 가능합니다. {existing_tool.status}")

        yield SSEEncoder.encode("generating", "도구 수정 중입니다.")

        from sage.secret.keys import prepare_tool_secret_fields

        secret_id = req.secret_id
        user_id = req.user_id or "admin"
        # 키 필드를 LLM 컨텍스트에 안전하게 주입할 수 있게 해석.
        resolved_secret_id, provider, keys = await prepare_tool_secret_fields(
            user_id=user_id,
            secret_id=secret_id,
            query=req.query,
        )

        tool_updator = nodes.nodes['tool/update']
        updated_tool = await tool_updator.run(
            query=req.query,
            ref_code=req.ref_code,
            tool_id=tool_id,
            tool=ToolPack(
                tool_id=tool_id,
                title=existing_tool.title,
                description=existing_tool.description,
                code=existing_tool.code,
                caller=existing_tool.caller,
            ),
            secret_id=resolved_secret_id,
            provider=provider,
            keys=keys,
            user_id=user_id,
        )

        yield SSEEncoder.encode("executing", "수정된 도구의 구문 및 로직을 검증합니다.")

        # 4. 검증 및 수정 (Auto-fix 로직 포함)
        # 구문 검사 상태 업데이트
        tool_status: doc.ToolStatus = "generated"
        tools.dump(
            updated_tool,
            tool_status,
            instructions=req.query or "",
            secret_id=resolved_secret_id or existing_tool.secret_id,
        )

        # 실제 실행 환경(docker_pool)에서 검증 — progress SSE
        reporter = TaskReporter()
        exec_task = asyncio.create_task(
            execute_with_fix(updated_tool, reporter=reporter)
        )
        async for msg in reporter.iter_while(exec_task):
            yield SSEEncoder.encode("progress", msg)
            await asyncio.sleep(0)
        _, validated_tool = await exec_task

        # 5. 동일 tool_id 로 upsert — 버전 fork 없이 in-place 수정.
        tool_doc = doc.Tool(
            tool_id=tool_id,
            title=validated_tool.title,
            description=validated_tool.description,
            code=validated_tool.code,
            caller=validated_tool.caller,
            status=tool_status,
            category=req.category,
            tags=req.tags,
            query=req.query,
            secret_id=resolved_secret_id,
        )

        await db.save(tool_doc)

        # JSON 직렬화 시 ensure_ascii=False 적용 (result 데이터 구성 시)
        result_data = validated_tool.model_dump(mode='json')

        yield SSEEncoder.encode(
            "completed",
            "도구 업데이트가 성공적으로 완료되었습니다.",
            tool_id=tool_id,
            result=result_data
        )

    except Exception as e:
        # 에러 로깅 및 전송
        error(f"도구 업데이트 오류 [{tool_id}]: {traceback.format_exc()}")

        yield SSEEncoder.encode(
            "failed",
            f"수정 프로세스 중단: {str(e)}",
            tool_id=tool_id
        )


@router.post("/assetize", response_model=APIResponse[AssetizeResponse])
async def assetize_tool(req: AssetizeRequest, db: SAGEDataStore = Depends(get_db)):
    """
    도구 자산화 — generate(tm-*) 또는 기존 경로(kis/stock)를 assetized 로 등록합니다.
    """
    # ------------------------------------------------------------------
    # assetize: generated 초안 또는 기존 폴더를 "운영 path" 로 승격.
    # - recommend/목록의 assetized 필터가 이 상태만 본다.
    # - 실제 이동·DB 상태 갱신은 perform_assetize 한곳에 모아 중복 방지.
    # ------------------------------------------------------------------
    try:
        if not req.tool_id and not req.tool_path:
            return APIResponse(
                success=False,
                error="tool_id 또는 tool_path 중 하나는 필수입니다.",
            )

        final_path = await perform_assetize(
            db,
            tool_id=req.tool_id,
            asset_path=req.asset_path,  # target
            tool_path=req.tool_path,  # source
            title=req.title,
            description=req.description,
        )

        return APIResponse(
            success=True,
            result=AssetizeResponse(asset_path=final_path, tool_id=final_path),
        )

    except FileNotFoundError as e:
        return APIResponse(success=False, error=str(e))
    except Exception as e:
        error(f"Assetize Error: {traceback.format_exc()}")
        return APIResponse(success=False, error=str(e), result=None)


@router.delete("/delete", response_model=DeleteResponse)
async def delete_tools(
        req: ToolDeleteRequest,
        saged: SAGEDataStore = Depends(get_db)
):
    """
    도구 일괄 삭제 API
    - all: 전체 도구 레코드 및 물리 디렉토리 삭제
    - exclude: 특정 tool_id 배열을 제외한 모든 도구 레코드 및 물리 디렉토리 삭제
    - list: 주어진 tool_id 배열에 해당하는 도구 레코드 및 물리 디렉토리 삭제
    """

    # 1. 모드별 타겟 tool_id 목록 추출
    target_tool_ids = []

    try:
        if req.mode == "all":
            # tm- 접두사를 활용하여 전체 도구 ID 목록 조회
            target_tool_ids = await saged.list_all_ids("tm-")

        elif req.mode == "exclude":
            if not req.ids:
                raise HTTPException(status_code=400, detail="exclude 모드에서는 제외할 tool_ids 배열이 필수입니다.")

            all_tool_ids = await saged.list_all_ids("tm-")
            exclude_set = set(req.ids)
            target_tool_ids = [tid for tid in all_tool_ids if tid not in exclude_set]

        elif req.mode == "list":
            if not req.ids:
                raise HTTPException(status_code=400, detail="list 모드에서는 삭제할 tool_ids 배열이 필수입니다.")
            target_tool_ids = req.ids

        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 mode 값입니다. ('all', 'exclude', 'list' 중 선택)")

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 대상 식별 중 오류: {str(e)}")

    if not target_tool_ids:
        return DeleteResponse(
            status="success",
            id=str(req.ids or []),
            message="삭제할 대상 도구가 없습니다."
        )

    # 2. 루프를 돌며 DB 메타데이터 및 물리 파일(tools/{tool_id}) 삭제 진행
    success_tids = []
    failed_tids = []

    for tool_id in target_tool_ids:
        try:
            # 2-1. 데이터베이스(doc.Tool) 삭제
            await saged.delete(tool_id)

            # 2-2. 파일 시스템(tools 하위 디렉토리) 삭제
            # 기존 코드인 cfg.tools_path / tool_id 구조 유지
            target_dir = cfg.tools_path / tool_id

            if target_dir.exists() and target_dir.is_dir():
                # 안전장치: cfg.tools_path를 이탈하는 비정상적인 경로 탐지
                if cfg.tools_path in target_dir.parents:
                    shutil.rmtree(target_dir)

            success_tids.append(tool_id)

        except Exception as e:
            print(f"tool_id {tool_id} 및 물리 파일 삭제 중 에러 발생")
            print(traceback.format_exc())
            failed_tids.append({"tool_id": tool_id, "reason": str(e)})

    # 3. 결과 반환
    status_str = "partial_success" if failed_tids else "success"

    return DeleteResponse(
        status=status_str,
        id=str(req.ids or []),
        message=f"요청된 대상 중 {len(success_tids)}개의 도구 레코드 및 물리 폴더가 삭제되었습니다."
    )