"""Data dataset API — upload, list, Pangea unify, and SSE integration flows."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import traceback
import uuid
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal, Union

import numpy as np
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
import pandas as pd

from fastapi import APIRouter, Depends
from fastapi import HTTPException, UploadFile, File
from sse_starlette import EventSourceResponse
# from fastapi.sse import EventSourceResponse

from sage import nodes
from sage.data.bridge import InMemoryDataBridge
from sage.data.pangeaze_guide import build_pangeaze_user_query
from sage.db import SAGEDataStore, saged, get_db
from sage.errs import ExecutionError, ServiceUnavailableError, MaxRetriesExceededError
from sage.llm import GeminiLLM
from sage.logg import error, LoggingRoute, warning
from sage.mcp import load_tools_spec, close_all_sessions
from routers.base import SSEEncoder, APIResponse
from sage.models.node import (
    FileSourceMetadata,
    ToolSourceMetadata,
    PangeaOutput,
)
from sage.models.req import DataListRequest, DataInfoRequest, PangeaUpdateRequest, DatasetDeleteRequest
from sage.data.metadata import DEFAULT_MODEL, PangeaDataMetadata
from sage.report.runner import TaskReporter, normalize_unify_reporter_calls
from sage.data.schema_types import normalize_schema_type, schema_type_to_pandas_dtype
from utils.mod import load_module

# from sage.nodes import DataExecutor

import cfg

router = APIRouter(
    prefix="/data",  # 공통 경로 접두어
    tags=["data"],  # Swagger 문서상의 그룹 이름
    route_class=LoggingRoute
)


class ColumnInfo(BaseModel):
    """컬럼명과 추론된 데이터 타입 정보"""
    name: str = Field(..., description="컬럼 이름")
    dtype: str = Field(..., description="데이터 타입 (string, number, datetime, boolean, object)")
    selected: bool = Field(default=False, description="통합 대상 컬럼 여부 (업로드 시 false, 요청 시 true로 지정)")


class Metadata(BaseModel):
    """시트 또는 파일의 구조 정보"""
    name: str = Field(..., description="시트명 또는 데이터셋 식별자")
    columns: List[ColumnInfo] = Field(..., description="추출된 컬럼 및 타입 목록")


class UploadResponse(BaseModel):
    """최종 API 응답 모델"""
    path: str
    filename: str
    file_type: str
    metadata: List[Metadata]


# --- 2. 데이터 타입 판별 유틸리티 ---

def map_dtype(pandas_dtype: Any, sample_value: Any = None) -> str:
    """
    Pandas dtypes와 샘플 데이터를 바탕으로 타입을 분류
    - 문자열로 표현되는 일반 텍스트: 'string'
    - 리스트, 딕셔너리 등 복합/특화 데이터: 'object'
    """
    dtype_str = str(pandas_dtype).lower()

    # 숫자형 (정수, 실수 등)
    if 'int' in dtype_str or 'float' in dtype_str or 'decimal' in dtype_str:
        return 'number'

    # 날짜/시간형
    elif 'datetime' in dtype_str:
        return 'datetime'

    # 논리형
    elif 'bool' in dtype_str:
        return 'boolean'

    # 문자열 및 객체형 세분화
    elif 'object' in dtype_str or 'string' in dtype_str:
        # 실제 데이터 값을 확인하여 단순 문자열인지 판단
        if sample_value is not None:
            # 리스트나 딕셔너리 같은 복합 객체인 경우
            if isinstance(sample_value, (list, dict, set, tuple)):
                return 'object'
            # 그 외 일반적인 문자열 형태
            return 'string'
        return 'string'

    return 'object'


# --- 3. 메타데이터 추출 코어 로직 ---

def extract_metadata(full_path: Path, extension: str) -> List[Metadata]:
    metadata_list = []
    try:
        # 1. Excel (.xlsx, .xls)
        if extension in ['.xlsx', '.xls']:
            with pd.ExcelFile(full_path, engine='openpyxl') as excel_file:
                for sheet in excel_file.sheet_names:
                    # 타입 추론을 위해 1행만 읽음
                    df_sample = pd.read_excel(excel_file, sheet_name=sheet, nrows=1)

                    column_infos = []
                    for col in df_sample.columns:
                        val = df_sample[col].iloc[0] if not df_sample[col].empty else None
                        column_infos.append(ColumnInfo(
                            name=col,
                            dtype=map_dtype(df_sample[col].dtype, val)
                        ))
                    metadata_list.append(Metadata(name=sheet, columns=column_infos))

        # 2. CSV (.csv)
        elif extension == '.csv':
            try:
                df_sample = pd.read_csv(full_path, nrows=1, encoding='utf-8')
            except UnicodeDecodeError:
                df_sample = pd.read_csv(full_path, nrows=1, encoding='cp949')

            column_infos = [
                ColumnInfo(
                    name=col,
                    dtype=map_dtype(df_sample[col].dtype,
                                    df_sample[col].iloc[0] if not df_sample[col].empty else None)
                ) for col in df_sample.columns
            ]
            metadata_list.append(Metadata(name="Sheet1", columns=column_infos))

        # 3. Parquet (.parquet)
        elif extension == '.parquet':
            import pyarrow.parquet as pq
            # Parquet은 스키마 정보가 풍부하지만, 일관성을 위해 1행을 읽어 판단
            table = pq.read_table(full_path).slice(0, 1)
            df_sample = table.to_pandas()

            column_infos = [
                ColumnInfo(
                    name=col,
                    dtype=map_dtype(df_sample[col].dtype,
                                    df_sample[col].iloc[0] if not df_sample[col].empty else None)
                ) for col in df_sample.columns
            ]
            metadata_list.append(Metadata(name="Sheet1", columns=column_infos))

        return metadata_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata 추출 실패: {str(e)}")


# --- 4. API 엔드포인트 ---

@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """파일 업로드 및 컬럼명/타입 정보 반환"""
    # ------------------------------------------------------------------
    # path 형식: "{uuid8}/{원본파일명}"
    # - 왜 절대경로가 아닌가? FE/후속 pangeaze 요청이 상대 path 만 들고 다니고,
    #   서버가 uploads/ 아래로 resolve 하기 때문 (멀티 호스트·배포에도 이식 용이).
    # - 왜 uuid 디렉토리인가? 동일 파일명 충돌 방지 + 업로드 스코프 격리.
    # - pangeaze 쪽은 src.path 의 첫 세그먼트(uuid)를 제외한 나머지를
    #   data/{did}/raw/ 로 복사한다 (uploads/{uuid}/foo.csv → raw/foo.csv).
    # ------------------------------------------------------------------

    # 파일 저장 경로 설정 (UUID 기반)
    temp_uuid = str(uuid.uuid4())[:8]
    file_path_str = f"{temp_uuid}/{file.filename}"

    # cfg.uploads_path (= project root/uploads) — pangeaze 읽기 경로와 동일 루트
    upload_base_path = Path(cfg.uploads_path)
    full_path = upload_base_path / file_path_str
    extension = Path(file.filename).suffix.lower()

    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    try:
        content = await file.read()
        with open(full_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 오류: {str(e)}")

    # 메타데이터는 컬럼 선택 UI 용 — selected 기본 false 로 내려 FE 가 골라냄.
    supported_extensions = ['.xlsx', '.xls', '.csv', '.parquet']
    metadata = []
    if extension in supported_extensions:
        metadata = extract_metadata(full_path, extension)

    # 응답 path 는 full_path 가 아니라 file_path_str (상대) — 위 계약 유지.
    response_obj = UploadResponse(
        path=file_path_str,
        filename=file.filename,
        file_type=extension.lstrip('.'),
        metadata=metadata
    )

    # 한글 깨짐 방지 및 JSON 직렬화 후 반환
    return json.loads(json.dumps(response_obj.model_dump(), ensure_ascii=False))


class Column(BaseModel):
    name: str
    type: str = Field("str", description="통합 스키마 canonical: str|int|float|bool|date|datetime")
    selected: bool = Field(default=False, description="로드/통합 대상 컬럼 여부")

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, v: Any) -> str:
        return normalize_schema_type(str(v))


def resolve_load_columns(
    column_defs: List[Column | dict] | None,
    legacy_columns: List[str] | None,
) -> List[Dict[str, str]] | List[str] | None:
    """
    FileSource/Sheet 컬럼 정의 → load_dataframe columns 인자.
    - column_defs: 전체 컬럼 목록(name, type, selected). selected=true 만 로드.
    - legacy_columns: (하위 호환) 컬럼명 문자열 목록 — 모두 로드 대상.
    - 둘 다 없으면 None → 파일의 모든 컬럼 로드.
    """
    # ------------------------------------------------------------------
    # 왜 이 변환 계층이 필요한가?
    # - 업로드/UI 는 "파일의 전체 컬럼 + selected 체크" 모델을 쓰고,
    #   load_dataframe 은 "실제로 읽을 컬럼(+타입 캐스팅)" 만 원한다.
    # - selected=false 컬럼까지 로드하면 메모리·프롬프트(sample)가 비대해지고
    #   LLM 이 불필요 필드를 스키마에 넣을 위험이 커진다.
    # - column_defs 가 있는데 selected 가 0개면 "의도적 전부 미선택"으로 보고
    #   silent full-load 대신 ValueError — UX 버그를 숨기지 않음.
    # - legacy_columns(문자열 목록)는 옛 API 호환; 있으면 전부 로드 대상.
    # ------------------------------------------------------------------
    if column_defs is not None:
        selected: List[Dict[str, str]] = []
        for raw in column_defs:
            col = raw if isinstance(raw, Column) else Column.model_validate(raw)
            if col.selected:
                # name+type 쌍: 로드 시 dtype 강제(normalize_schema_type 경유).
                selected.append({"name": col.name, "type": col.type})
        if column_defs and not selected:
            raise ValueError("selected=true 인 컬럼이 없습니다.")
        return selected or None
    if legacy_columns:
        return legacy_columns
    return None


def load_dataframe(
    file_path: str,
    options: dict,
    columns: List[Dict[str, str]] | List[str] | None = None,
    **kwargs,
) -> pd.DataFrame:
    """파일 로드 → 지정 컬럼만 선택하고 canonical type 으로 캐스팅해 반환.

    columns: ``[{name, type}, ...]`` 또는 legacy ``['col', ...]``.
    """
    ext = os.path.splitext(file_path)[-1].lower()

    usecols: Any | None = None
    typed_columns: List[Dict[str, str]] | None = None
    if columns:
        first = columns[0]
        if isinstance(first, dict):
            typed_columns = columns  # type: ignore[assignment]
            usecols = [c["name"] for c in columns]  # type: ignore[index]
        else:
            usecols = columns

    if ext == ".csv":
        df = pd.read_csv(
            file_path,
            encoding=options.get("encoding", "utf-8"),
            usecols=usecols,
            **kwargs,
        )
    elif ext in [".xlsx", ".xls"]:
        sheet_name = options.get("sheet_name", 0)
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            usecols=usecols,
            engine="openpyxl",
            **kwargs,
        )
    elif ext == ".parquet":
        df = pd.read_parquet(file_path, columns=usecols)
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")

    if typed_columns:
        for col in typed_columns:
            name = col["name"]
            if name not in df.columns:
                continue
            try:
                canonical = normalize_schema_type(col["type"])
                target_dtype = schema_type_to_pandas_dtype(canonical)
                if canonical == "date":
                    df[name] = pd.to_datetime(df[name], errors="coerce").dt.date
                else:
                    df[name] = df[name].astype(target_dtype, errors="ignore")
            except Exception as e:
                print(f"컬럼 {name} 타입 변환 오류 ({col.get('type')}): {e}")

    return df


def _load_stored_file_dataframe(file_path: Path, src: dict) -> pd.DataFrame:
    """Mongo sources[] + raw/ 파일 → DataFrame (update 경로용)."""
    load_options = dict(src.get("load_options") or src.get("options") or {})
    column_defs = None
    sheets = src.get("sheets") or []
    if sheets:
        sheet_name = load_options.get("sheet_name", 0)
        for sh in sheets:
            if sh.get("name") == sheet_name or str(sh.get("name")) == str(sheet_name):
                column_defs = sh.get("columns")
                break
        if column_defs is None and len(sheets) == 1:
            column_defs = sheets[0].get("columns")
    cols = resolve_load_columns(column_defs, src.get("columns"))
    return load_dataframe(str(file_path), load_options, columns=cols)


class Sheet(BaseModel):
    name: str = Field(default_factory="Sheet1", description="시트 이름")
    columns: List[Column] | None = Field(
        default=None,
        description="파일의 전체 컬럼 정의. selected=true 인 컬럼만 로드. None 이면 모든 컬럼 대상",
    )


class FileSource(BaseModel):
    type: Literal["file"] = "file"
    path: str
    format: Optional[Literal["csv", "xlsx"]] = Field(default=None)
    columns: Optional[List[str]] = Field(default=None, description="(legacy) 로드할 컬럼명 목록 — 모두 selected 로 간주")
    sheets: Optional[List[Sheet]] = Field(default=None)
    options: Dict[str, Any] = Field(
        default={
            "header": True,
            "encoding": "utf-8",
        }
    )

    @model_validator(mode='after')
    def set_format_from_path(self) -> 'FileSource':
        if self.format is not None:
            return self

        _, ext = os.path.splitext(self.path)
        ext = ext.lower().lstrip('.')

        if not self.format:
            if ext == "csv":
                self.format = "csv"
            elif ext in ["xlsx", "xls"]:
                self.format = "xlsx"

        return self


class DBSource(BaseModel):
    type: Literal["db"] = "db"
    connection: Dict[str, Any]  # host, port, user, password, database, target
    description: Optional[str] = ""


class ToolSource(BaseModel):
    type: Literal["tool"] = "tool"
    path: str = Field(..., description="도구 호출 경로 (서버명/도구명)")
    # tool_spec: Dict[str, Any] = Field(..., description="JSON 명세")


#     )


@router.get("/view")
async def view_data(
        did: str,
        limit: int = 10,
        model: str = DEFAULT_MODEL,
):
    """
    데이터 확인 및 샘플링.
    metadata.json targets[].path 기준 parquet 로드 (기본 model=PangeaSchema).
    """
    data_meta = await saged.get(did)
    if not data_meta:
        raise HTTPException(status_code=404, detail="데이터셋을 찾을 수 없습니다.")

    version = data_meta.get("version", "v1")
    pangea_meta = PangeaDataMetadata.from_did(did, version)

    try:
        sampled_data, target_info = pangea_meta.sample_records(model=model, limit=limit)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 처리 중 오류 발생: {str(e)}") from e

    safe_data = jsonable_encoder(sampled_data)
    return {
        "model": target_info["model"],
        "path": target_info["path"],
        "keys": target_info["keys"],
        "fields": target_info["fields"],
        "data": safe_data or [],
    }



@router.post("/list/query", response_model=APIResponse[List[Dict[str, Any]]])
async def list_data(
    req: DataListRequest, 
    saged: SAGEDataStore = Depends(get_db)
):
    """
    데이터셋 목록 조회 (JSON Body 요청)
    - status가 없거나 빈 배열이면 전체 데이터셋 조회
    - status에 ["completed", "failed"] 등 배열을 전달하면 해당 상태들을 OR 조건으로 필터링
    - category 로 데이터셋 카테고리 필터 (예: finance)
    """
    try:
        # 요구사항에 맞게 'did-' 식별자를 기반으로 컬렉션 로드
        col = saged.get_collection('did-')
        
        # 1. status / category 조건에 따른 MongoDB 쿼리 구성
        query = {}
        if req.status:
            query["status"] = {"$in": req.status}
        if req.category:
            query["category"] = req.category

        # 2. DB 조회 진행
        cursor = col.find(query)
        data_list = []
        
        async for cur in cursor:
            # MongoDB 고유의 ObjectId 오브젝트가 존재할 경우 JSON 직렬화를 위해 문자열 변환 처리
            if "_id" in cur:
                cur["_id"] = str(cur["_id"])
            data_list.append(cur)

        return APIResponse[List[Dict[str, Any]]](success=True, result=data_list)

    except Exception as e:
        return APIResponse[List[Dict[str, Any]]](
            success=False,
            error=f"데이터셋 목록을 불러오는 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/info", response_model=APIResponse[Dict[str, Any]])
async def info_data(
    req: DataInfoRequest,
    saged: SAGEDataStore = Depends(get_db),
):
    """
    데이터셋 상세 조회 (JSON Body 요청)
    - did 로 단일 데이터셋 문서를 반환합니다.
    """
    try:
        data_doc = await saged.get(req.did)
        if not data_doc:
            return APIResponse[Dict[str, Any]](
                success=False,
                error=f"데이터셋을 찾을 수 없습니다: {req.did}",
            )

        if "_id" in data_doc:
            data_doc["_id"] = str(data_doc["_id"])

        return APIResponse[Dict[str, Any]](
            success=True,
            result=jsonable_encoder(data_doc),
        )

    except Exception as e:
        return APIResponse[Dict[str, Any]](
            success=False,
            error=f"데이터셋 정보를 불러오는 중 오류가 발생했습니다: {str(e)}",
        )



async def generate_did_via_llm(name: str) -> str:
    slug = await GeminiLLM().generate_async(
        f"다음 이름을 영문 소문자 또는 - (dash)를 이용해서 바꾸어죠. \n"
        f"-허용 문자: 소문자,-\n"
        f"-불허 문자: 스페이스 포함 기타 문자 모두 불허\n"
        f"-최대 30자 이내\n"
        f"ex. [type]-[feature]. type: stock, property; feature: kospi100, lowperpbr, ..."
        f"이름: {name}. 결과만 리턴하라\n"
    )

    if not slug: slug = "dataset"

    unique_suffix = str(uuid.uuid4())[:8]
    return f"did-{slug}-{unique_suffix}"



def _exec_pydantic_schema_code(pydantic_code: str) -> dict[str, Any]:
    """schema.py 소스를 exec 하여 BaseModel 서브클래스 dict 를 반환. 실패 시 {"error": ...}."""
    local_scope: dict[str, Any] = {
        "BaseModel": BaseModel,
        "Field": Field,
        "ConfigDict": ConfigDict,
        "List": List,
        "Dict": Dict,
        "Any": Any,
        "Optional": Optional,
        "Union": Union,
        "date": date,
        "datetime": datetime,
    }

    try:
        exec(pydantic_code, globals(), local_scope)
    except Exception as e:
        return {"error": f"스키마 코드 실행 실패: {str(e)}"}

    models = {
        name: obj
        for name, obj in local_scope.items()
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel
    }
    if not models:
        return {"error": "schema.py 에서 BaseModel 서브클래스를 찾을 수 없습니다."}

    for model in models.values():
        model.model_rebuild(_types_namespace=local_scope)

    return models


def extract_schema_info(
    pydantic_code: str,
    main_class_name: str = "PangeaSchema",
    model_names: list[str] | None = None,
) -> dict:
    """
    텍스트로 된 Pydantic 코드를 실행하여 JSON Schema를 추출합니다.
    - 기본: main_class_name 의 JSON Schema (FE 표준 매핑 패널용)
    - model_names 지정 시: {"schema": ..., "schemas": {model: json_schema}} 형태로 다중 모델 포함
    """
    models_or_error = _exec_pydantic_schema_code(pydantic_code)
    if "error" in models_or_error:
        return models_or_error

    models: dict[str, type[BaseModel]] = models_or_error
    main_model = models.get(main_class_name)
    if not main_model:
        return {
            "error": f"클래스 '{main_class_name}'을(를) 찾을 수 없거나 유효한 BaseModel이 아닙니다."
        }

    main_schema = main_model.model_json_schema()
    if not model_names:
        return main_schema

    ordered_names = model_names or list(models.keys())
    schemas = {
        name: models[name].model_json_schema()
        for name in ordered_names
        if name in models
    }
    return {"schema": main_schema, "schemas": schemas}


# 통합 PangeaRequest 모델
class PangeaRequest(BaseModel):
    name: str = Field(description="통합 데이터 제목(이름)")
    query: str = Field("최대한 등록데이터 항목을 많이 활용하라. 상세한 데이터 스키마를 설정.", description="LLM에게 전달할 데이터 통합/분석 요구사항")
    description: Optional[str] = Field(default=None, description="통합 데이터 부가 설명")
    category: str | None = Field(None, description="데이터셋 카테고리 (예: finance, hr)")
    sources: List[Union[FileSource, ToolSource, DBSource]]
    options: Dict[str, Any] = Field(default={"pseudonymization": False})

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "상장사 재무 분석 통합",
                "query": "주식 목록 파일과 KIS API의 PER, PBR 데이터를 srtnCd 기준으로 통합해줘",
                "description": "description 을 작성하세요.",
                "category": "finance",
                "sources": [
                    {
                        "type": "file",
                        "path": "uploaded/stocks.csv",
                        "format": "csv",
                        "options": {"encoding": "utf-8"},
                        "sheets": [
                            {
                                "name": "Sheet1",
                                "columns": [
                                    {"name": "srtnCd", "type": "str", "selected": True},
                                    {"name": "itmsNm", "type": "str", "selected": True},
                                    {"name": "mrktCtg", "type": "str", "selected": False},
                                    {"name": "clpr", "type": "float", "selected": True},
                                ],
                            }
                        ],
                    },
                    {
                        "type": "file",
                        "path": "uploaded/financials.xlsx",
                        "format": "xlsx",
                        "options": {"header": True},
                        "sheets": [
                            {
                                "name": "Sheet1",
                                "columns": [
                                    {"name": "basDt", "type": "date", "selected": True},
                                    {"name": "srtnCd", "type": "str", "selected": True},
                                    {"name": "isinCd", "type": "str", "selected": False},
                                    {"name": "itmsNm", "type": "str", "selected": True},
                                    {"name": "clpr", "type": "float", "selected": True},
                                ],
                            }
                        ],
                    },
                    {
                        "type": "tool",
                        "path": "kis/stock",
                    },
                ],
            }
        }
    )


@router.post("/pangeaze")
async def pangeaze(req: PangeaRequest, saged: SAGEDataStore = Depends(get_db)):
    """
    1단계: 등록 + 분석 + 통합을 한 번에 수행하는 All-in-One API
    - 소스 데이터 배치
    - DataPangeazer 노드를 통한 스키마/로직 생성
    - 생성된 로직의 동적 실행 및 결과 저장
    """
    return EventSourceResponse(
        handle_pangeaze(req, saged)
    )


PANGEAZE_UNIFY_MAX_ATTEMPTS = 3


def _write_pangea_assets(pangea_path: Path, pangea_result: PangeaOutput) -> None:
    assets = {
        "metadata.json": json.dumps(pangea_result.metadata, ensure_ascii=False, indent=2),
        "schema.py": pangea_result.schema_code,
        "adapter.py": pangea_result.adapter,
        "unify.py": normalize_unify_reporter_calls(pangea_result.unify_logic_code),
    }
    for name, content in assets.items():
        with open(pangea_path / name, "w", encoding="utf-8") as f:
            f.write(content)


def _invalidate_pangea_modules() -> None:
    for name in ("schema", "adapter", "unify"):
        sys.modules.pop(name, None)


def _save_unify_parquets(
    pangea_path: Path,
    results: dict[str, pd.DataFrame],
    metadata: dict[str, Any],
) -> None:
    """unify_data 반환 dict → target별 ``{key}.parquet`` (create/update 공통)."""
    targets = metadata.get("targets") or []
    for key, df in results.items():
        file_path = pangea_path / f"{key}.parquet"
        df.to_parquet(file_path, index=False)
        target_config = next((t for t in targets if key in str(t.get("path", ""))), None)
        if not target_config:
            print(f"Warning: Model with path containing {key} not found in metadata.")


def _prepare_unify_on_host(pangea_path: Path) -> None:
    """control plane — reporter 호출 정규화 (worker 실행 전)."""
    unify_path = pangea_path / "unify.py"
    unify_text = unify_path.read_text(encoding="utf-8")
    fixed_unify = normalize_unify_reporter_calls(unify_text)
    if fixed_unify != unify_text:
        unify_path.write_text(fixed_unify, encoding="utf-8")


def _stage_bridge_for_exec(did: str, dataset_root: Path) -> None:
    """InMemoryDataBridge → ``data/{did}/.bridge/`` (docker worker hydrate)."""
    InMemoryDataBridge.export_staging(did, dataset_root / ".bridge")


def _load_unify_results(pangea_path: Path, keys: list[str]) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}
    for key in keys:
        path = pangea_path / f"{key}.parquet"
        if not path.is_file():
            raise ExecutionError(f"unify parquet 없음: {path}")
        results[key] = pd.read_parquet(path)
    return results


async def _run_unify_data(
    did: str,
    pangea_path: Path,
    reporter: TaskReporter,
) -> dict[str, pd.DataFrame]:
    """create/update common path — unify via docker_pool exec.

    schema/adapter/unify.py is loaded in the worker. Host prepares reporter
    normalization and bridge staging; SSE progress is polled via reporter.drain().
    """
    _prepare_unify_on_host(pangea_path)
    dataset_root = pangea_path.parent.parent
    _stage_bridge_for_exec(did, dataset_root)

    from sage.exec.jobs import build_pangea_unify_job
    from sage.exec.runtime import run_exec_job

    job = build_pangea_unify_job(did=did, pangea_path=pangea_path)
    result = await run_exec_job(job, reporter=reporter)

    if not result.ok:
        raise ExecutionError(result.error or "unify exec failed")

    keys = (result.return_value or {}).get("keys") or []
    if not keys:
        raise ExecutionError("unify_data 결과 keys 없음")
    return _load_unify_results(pangea_path, keys)


def _pangeaze_user_query(
    base_query: str,
    sources_meta: list,
    unify_error: str = "",
) -> str:
    """첫 codegen 부터 파일/도구 source_id 가이드를 붙인다. 실행 실패 시 에러 tail 추가."""
    return build_pangeaze_user_query(
        base_query, sources_meta, unify_error=unify_error
    )


async def handle_pangeaze(req: PangeaRequest, db: SAGEDataStore):
    """All-in-one dataset registration: sources → schema → unify → persist.

    Args:
        req: Pangea request (name, sources, query, options).
        db: Store for ``did-*`` dataset documents.

    Yields:
        SSE progress events through unify retries and final ``completed`` / ``error``.
    """
    # ==================================================================
    # Pangeaze 페이즈 (SSE event 와 대응)
    # A. initializing — did 발급, raw/ 준비
    # B. source 루프 — file/tool 각각 영속화 + LLM용 메타(sample) 구성
    # C. unify retry 루프 (최대 PANGEAZE_UNIFY_MAX_ATTEMPTS)
    #    generating → assets 기록 → executing → progress(SSE drain)
    # D. parquet 저장 + db.put(did 문서) → completed
    # 실패 시 lesson_exception 으로 노드 validated.md 학습, finally 에서
    # MCP 세션·InMemoryDataBridge 정리 (프로세스 오염 방지).
    # ==================================================================
    did = None
    try:
        yield SSEEncoder.encode("initializing", f"데이터셋 [{req.name}] 멀티 소스 초기화 중")

        # LLM slug + uuid — 사람이 읽는 이름 + 전역 고유성.
        did = await generate_did_via_llm(req.name)
        dataset_root = Path(cfg.root_path) / "data" / did
        raw_dir = dataset_root / "raw"
        os.makedirs(raw_dir, exist_ok=True)

        processed_sources = []   # Mongo did 문서용 sources[] (update 시 재로드 키)
        sources_meta = []        # DataPangeazer 노드 attach용 메타 (샘플 위주)

        # --- Phase B: source loop ---
        for src in req.sources:
            if src.type == "file":
                # upload("{uuid}/{name}") → data/{did}/raw/{name} 으로 승격.
                # uploads 는 임시, raw 가 데이터셋의 소스 오브 트루스.
                # 루트는 cfg.uploads_path (= upload_file 과 동일, cwd 무관)
                temp_path = Path(cfg.uploads_path) / src.path
                if not temp_path.exists():
                    raise FileNotFoundError(f"임시 파일을 찾을 수 없습니다: {src.path}")

                # parts[1:]: uuid 세그먼트 제거 → raw 아래엔 파일명만 유지.
                target_path = Path(*Path(src.path).parts[1:]).as_posix()
                shutil.copy2(temp_path, raw_dir / target_path)

                def append_file_source(
                    s_id,
                    df: pd.DataFrame,
                    *,
                    column_defs: list[dict] | None = None,
                    load_options: dict | None = None,
                ):
                    # sources_meta: LLM 프롬프트용(샘플·컬럼) / processed_sources: DB 영속.
                    # 둘을 갈라 두는 이유 — 메타는 크기를 제한하고, DB 쪽은 재실행에
                    # 필요한 origin/load_options 를 전부 보존해야 함.
                    sources_meta.append(FileSourceMetadata(
                        source_id=s_id,
                        path=target_path,
                        columns=df.columns.tolist(),
                        column_defs=column_defs,
                        column_types=df.dtypes.apply(lambda x: x.name).to_dict(),
                        sample_data=df.head(3).to_dict(orient='records'),
                        file_format=Path(src.path).suffix[1:]
                    ))
                    entry = {**src.model_dump(), "id": s_id, "origin": target_path}
                    if load_options is not None:
                        entry["load_options"] = load_options
                    processed_sources.append(entry)

                options = src.options.copy()
                if src.format == "csv":
                    s_id = f"src-{str(uuid.uuid4())[:8]}"
                    sheet_cols = src.sheets[0].columns if src.sheets and src.sheets[0].columns else None
                    column_defs = [c.model_dump() for c in sheet_cols] if sheet_cols else None
                    cols = resolve_load_columns(sheet_cols, src.columns)
                    df = load_dataframe(str(raw_dir / target_path), options, columns=cols)
                    # unify.py 가 런타임에 did+s_id 로 DataFrame 을 찾을 수 있게 등록.
                    InMemoryDataBridge.register(did, s_id, df)
                    append_file_source(s_id, df, column_defs=column_defs, load_options=options)
                elif src.format == "xlsx":
                    # 시트별 src-id — 한 파일이어도 LLM/unify 입장에선 독립 소스.
                    sheets = src.sheets or [Sheet(name=src.options.get("sheet_name", "Sheet1"))]
                    for sheet in sheets:
                        s_id = f"src-{str(uuid.uuid4())[:8]}"
                        load_options = {**options, "sheet_name": sheet.name}
                        column_defs = [c.model_dump() for c in sheet.columns] if sheet.columns else None
                        cols = resolve_load_columns(sheet.columns, src.columns)
                        df = load_dataframe(str(raw_dir / target_path), load_options, columns=cols)
                        InMemoryDataBridge.register(did, s_id, df)
                        append_file_source(
                            s_id, df, column_defs=column_defs, load_options=load_options
                        )
                else:
                    warning(f"파일 포맷(format) 오류: {src.path} ")

            elif src.type == "tool":
                # 파일과 달리 즉시 DataFrame 을 만들지 않음 — unify 가 MCP call 로 가져옴.
                # 여기선 tool_spec 만 붙어 LLM 이 경로·스키마를 인지하게 함.
                s_id = f"src-{str(uuid.uuid4())[:8]}"
                tools_spec = await load_tools_spec([src.path])
                spec = json.loads(tools_spec[0]) if tools_spec else {}
                sources_meta.append(ToolSourceMetadata(
                    source_id=s_id,
                    tool_path=src.path,
                    tool_spec=spec
                ))
                processed_sources.append({**src.model_dump(), "id": s_id, "origin": src.path})

        pangeazer_node = nodes.nodes['data/pangeaze']
        # 최초 생성은 항상 v1 — update 경로에서만 v2+ 를 쌓음.
        pangea_path = dataset_root / "pangea" / "v1"
        os.makedirs(pangea_path, exist_ok=True)

        pangea_result: PangeaOutput | None = None
        results: dict[str, pd.DataFrame] | None = None
        last_unify_error = ""

        # --- Phase C: unify retry ---
        # codegen 과 실행을 한 시도로 묶는 이유: schema/adapter/unify 가 어긋나면
        # 부분 수정 대신 에러 tail 을 붙인 전체 재생성이 성공률이 높다.
        for attempt in range(PANGEAZE_UNIFY_MAX_ATTEMPTS):
            # unify_data 실행 실패 시 에러 tail 을 query 에 붙여 schema/adapter/unify 전체 재생성
            if attempt == 0:
                yield SSEEncoder.encode("generating", "통합 스키마 코드 생성 중")
            else:
                yield SSEEncoder.encode(
                    "generating",
                    f"unify 실패 — 스키마/로직 재생성 중 ({attempt + 1}/{PANGEAZE_UNIFY_MAX_ATTEMPTS})",
                )

            user_query = _pangeaze_user_query(
                req.query, sources_meta, unify_error=last_unify_error
            )
            pangea_result = await pangeazer_node.run(
                dataset_name=req.name,
                user_query=user_query,
                sources=sources_meta,
            )
            _write_pangea_assets(pangea_path, pangea_result)
            # 이전 attempt 의 schema/adapter/unify 모듈 캐시 제거 — import 오염 방지.
            _invalidate_pangea_modules()

            exec_label = "통합 스키마 로직 실행 중"
            if attempt > 0:
                exec_label += f" (시도 {attempt + 1}/{PANGEAZE_UNIFY_MAX_ATTEMPTS})"
            yield SSEEncoder.encode("executing", exec_label)

            reporter = TaskReporter()
            exec_failed = False
            try:
                task = asyncio.create_task(_run_unify_data(did, pangea_path, reporter))

                # SSE 진행 배수: unify 가 블로킹되어도 drain 으로 progress 이벤트를 밀어줌.
                while True:
                    for msg in reporter.drain():
                        yield SSEEncoder.encode("progress", msg)
                    if task.done():
                        break
                    await asyncio.sleep(0.1)

                results = await task
            except Exception as e:
                exec_failed = True
                last_unify_error = traceback.format_exc()
                error(f"pangeaze execute attempt {attempt + 1} failed: {last_unify_error}")
                # 런타임 실패도 노드 lesson 에 축적 → 다음 재생성 프롬프트에 반영.
                await pangeazer_node.lesson_exception(e)
                if attempt + 1 >= PANGEAZE_UNIFY_MAX_ATTEMPTS:
                    raise ExecutionError(
                        f"통합 실행 실패 ({PANGEAZE_UNIFY_MAX_ATTEMPTS}회 시도): {e}"
                    ) from e
                yield SSEEncoder.encode(
                    "progress",
                    f"실행 실패(schema/adapter/unify) — 재생성 후 재시도 ({attempt + 2}/{PANGEAZE_UNIFY_MAX_ATTEMPTS})",
                )

            if not exec_failed:
                break

        if pangea_result is None or results is None:
            raise ExecutionError("unify_data 결과 없음")

        # --- Phase D: persist artifacts + Mongo ---
        metadata = pangea_result.metadata
        _save_unify_parquets(pangea_path, results, metadata)

        target_models = [
            t["model"] for t in metadata.get("targets", []) if t.get("model")
        ]
        schema_bundle = extract_schema_info(
            pangea_result.schema_code,
            model_names=target_models or None,
        )
        if "error" in schema_bundle:
            schema, schemas = schema_bundle, None
        elif "schema" in schema_bundle:
            schema, schemas = schema_bundle["schema"], schema_bundle.get("schemas")
        else:
            schema, schemas = schema_bundle, None

        # did 문서는 Pydantic 모델이 아닌 raw dict → save() 대신 put().
        doc = {
            "_id": did, "name": req.name,
            "description": req.description,
            "category": req.category,
            "status": "completed",
            "sources": processed_sources,
            "options": req.options,
            "suggested_queries": pangea_result.suggested_queries,
            "pangea": [
                {"version": "v1",
                 "schema": pangea_result.schema_code,
                 "metadata": pangea_result.metadata,
                 "created_at": datetime.now(timezone.utc)}],
            "updated_at": datetime.now(timezone.utc)
        }
        await db.put(doc)

        yield SSEEncoder.encode("completed", "Pangeaze 프로세스 완료: 스키마 기반 멀티 소스 통합 성공",
                                did=did, version="v1",
                                schema=schema,
                                schemas=schemas,
                                metadata=metadata,
                                suggested_queries=pangea_result.suggested_queries)

    except ServiceUnavailableError as e:
        yield SSEEncoder.encode("error", str(e))
    except MaxRetriesExceededError as e:
        from sage.nodes.lesson_learn import compress_error_for_lesson

        detail = compress_error_for_lesson(e.last_error) or (e.last_error or str(e)).strip()
        error(f"pangeaze codegen 실패 (재시도 {e.max_retries}회):\n{detail}")
        yield SSEEncoder.encode("error", f"통합데이터 구축 실패: {detail[:1500]}")
    except Exception as e:
        err_msg = traceback.format_exc()
        error(err_msg)
        yield SSEEncoder.encode("error", f"통합데이터 구축 실패: {e}")
    finally:
        # MCP 세션·브릿지 잔존 시 다음 요청이 잘못된 did/세션을 붙잡을 수 있음.
        try:
            await close_all_sessions()
        except Exception:
            pass
        if did:
            InMemoryDataBridge.clear_dataset(did)


@router.post("/pangeaze/update")
async def update_pangeaze(req: PangeaUpdateRequest, saged: SAGEDataStore = Depends(get_db)):
    """
    확정 스키마 기준으로 schema/adapter/unify 를 재생성하고 unify_data(did, reporter) 실행.
    결과는 새 pangea/v{n}/ 에 multi-target parquet 로 저장.
    """
    return EventSourceResponse(
        handle_pangeaze_update(req, saged)
    )


async def handle_pangeaze_update(req: PangeaUpdateRequest, db: SAGEDataStore):
    """Update path — create 와 동일 unify 계약: load_module + unify_data(did, reporter).

    Args:
        req: ``did`` + ``confirmed_schema``.
        db: 기존 데이터셋 문서 로드·이력 $push.

    Yields:
        SSE: initializing → generating → executing → progress → completed | error.
    """
    # create 와의 차이점만:
    # - did 재발급 없음 / uploads 복사 없음 — raw/ + sources[] 재로드
    # - confirmed_schema 로 LLM 재생성 제약
    # - pangea/v{n+1} 추가 + Mongo $push (v1 보존)
    # unify 시그니처·로더·parquet 저장은 create 와 공유 (_run_unify_data / _save_unify_parquets)
    did = req.did
    try:
        doc = await db.get(did)
        if not doc:
            raise Exception(f"데이터셋 {did}을 찾을 수 없습니다.")

        dataset_root = Path(cfg.root_path) / "data" / did
        raw_dir = dataset_root / "raw"

        yield SSEEncoder.encode("initializing", f"데이터셋 [{doc['name']}] 업데이트 및 소스 로드 중")

        sources_meta = []
        processed_sources = doc.get("sources", [])

        for src in processed_sources:
            s_id = src.get("id")
            s_type = src.get("type")
            origin = src.get("origin")

            if s_type == "file":
                file_path = raw_dir / origin
                if not file_path.exists():
                    warning(f"update: raw 파일 없음 — skip {origin}")
                    continue
                df = _load_stored_file_dataframe(file_path, src)
                # create 와 같이 Bridge 등록 — unify_data(did, …) 가 get(did, source_id) 사용
                InMemoryDataBridge.register(did, s_id, df)
                column_defs = None
                sheets = src.get("sheets") or []
                load_options = src.get("load_options") or src.get("options") or {}
                if sheets:
                    sheet_name = load_options.get("sheet_name", 0)
                    for sh in sheets:
                        if sh.get("name") == sheet_name or str(sh.get("name")) == str(sheet_name):
                            column_defs = sh.get("columns")
                            break
                    if column_defs is None and len(sheets) == 1:
                        column_defs = sheets[0].get("columns")
                sources_meta.append(FileSourceMetadata(
                    source_id=s_id,
                    path=origin,
                    columns=df.columns.tolist(),
                    column_defs=column_defs,
                    column_types=df.dtypes.apply(lambda x: x.name).to_dict(),
                    sample_data=df.head(3).to_dict(orient="records"),
                    file_format=Path(origin).suffix[1:],
                ))

            elif s_type == "tool":
                tools_spec = await load_tools_spec([origin])
                spec = json.loads(tools_spec[0]) if tools_spec else {}
                sources_meta.append(ToolSourceMetadata(
                    source_id=s_id,
                    tool_path=origin,
                    tool_spec=spec,
                ))

        current_pangea = doc.get("pangea", [])
        version = f"v{len(current_pangea) + 1}"
        pangea_path = dataset_root / "pangea" / version
        os.makedirs(pangea_path, exist_ok=True)

        pangeazer_node = nodes.nodes["data/pangeaze"]
        pangea_result: PangeaOutput | None = None
        results: dict[str, pd.DataFrame] | None = None
        last_unify_error = ""
        schema_json = json.dumps(req.confirmed_schema, ensure_ascii=False, indent=2)
        base_query = (
            "다음 확정된 스키마를 준수하여 schema/adapter/unify 를 재생성하라.\n"
            "unify_data(did, reporter=None) -> Dict[str, pd.DataFrame] 계약을 유지하라.\n"
            f"```json\n{schema_json}\n```"
        )

        for attempt in range(PANGEAZE_UNIFY_MAX_ATTEMPTS):
            if attempt == 0:
                yield SSEEncoder.encode("generating", "확정 스키마 기반 통합 로직 및 어댑터 재생성 중")
            else:
                yield SSEEncoder.encode(
                    "generating",
                    f"unify 실패 — 스키마/로직 재생성 중 ({attempt + 1}/{PANGEAZE_UNIFY_MAX_ATTEMPTS})",
                )

            user_query = _pangeaze_user_query(
                base_query, sources_meta, unify_error=last_unify_error
            )
            pangea_result = await pangeazer_node.run(
                dataset_name=doc["name"],
                user_query=user_query,
                sources=sources_meta,
                confirmed_schema=req.confirmed_schema,
            )
            _write_pangea_assets(pangea_path, pangea_result)

            exec_label = "통합 스키마 로직 실행 중"
            if attempt > 0:
                exec_label += f" (시도 {attempt + 1}/{PANGEAZE_UNIFY_MAX_ATTEMPTS})"
            yield SSEEncoder.encode("executing", exec_label)

            reporter = TaskReporter()
            exec_failed = False
            try:
                task = asyncio.create_task(_run_unify_data(did, pangea_path, reporter))
                while True:
                    for msg in reporter.drain():
                        yield SSEEncoder.encode("progress", msg)
                    if task.done():
                        break
                    await asyncio.sleep(0.1)
                results = await task
            except Exception as e:
                exec_failed = True
                last_unify_error = traceback.format_exc()
                error(f"pangeaze update execute attempt {attempt + 1} failed: {last_unify_error}")
                await pangeazer_node.lesson_exception(e)
                if attempt + 1 >= PANGEAZE_UNIFY_MAX_ATTEMPTS:
                    raise ExecutionError(
                        f"통합 실행 실패 ({PANGEAZE_UNIFY_MAX_ATTEMPTS}회 시도): {e}"
                    ) from e
                yield SSEEncoder.encode(
                    "progress",
                    f"실행 실패 — 재생성 후 재시도 ({attempt + 2}/{PANGEAZE_UNIFY_MAX_ATTEMPTS})",
                )

            if not exec_failed:
                break

        if pangea_result is None or results is None:
            raise ExecutionError("unify_data 결과 없음")

        _save_unify_parquets(pangea_path, results, pangea_result.metadata)

        new_entry = {
            "version": version,
            "schema": pangea_result.schema_code,
            "metadata": pangea_result.metadata,
            "created_at": datetime.now(timezone.utc),
        }
        await db.db["data"].update_one(
            {"_id": did},
            {
                "$set": {
                    "status": "completed",
                    "suggested_queries": pangea_result.suggested_queries,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$push": {"pangea": new_entry},
            },
        )

        target_models = [
            t["model"] for t in pangea_result.metadata.get("targets", []) if t.get("model")
        ]
        schema_bundle = extract_schema_info(
            pangea_result.schema_code,
            model_names=target_models or None,
        )
        if "error" in schema_bundle:
            schema_info, schemas = schema_bundle, None
        elif "schema" in schema_bundle:
            schema_info, schemas = schema_bundle["schema"], schema_bundle.get("schemas")
        else:
            schema_info, schemas = schema_bundle, None
        yield SSEEncoder.encode(
            "completed",
            f"업데이트 완료: {version} 생성 성공",
            did=did,
            version=version,
            schema=schema_info,
            schemas=schemas,
            metadata=pangea_result.metadata,
            suggested_queries=pangea_result.suggested_queries,
        )

    except ServiceUnavailableError as e:
        yield SSEEncoder.encode("error", str(e))
    except MaxRetriesExceededError as e:
        from sage.nodes.lesson_learn import compress_error_for_lesson

        detail = compress_error_for_lesson(e.last_error) or (e.last_error or str(e)).strip()
        error(f"pangeaze update codegen 실패 (재시도 {e.max_retries}회):\n{detail}")
        yield SSEEncoder.encode("error", f"업데이트 실패: {detail[:1500]}")
    except Exception as e:
        err_msg = traceback.format_exc()
        error(err_msg)
        yield SSEEncoder.encode("error", f"업데이트 실패: {e}")
    finally:
        try:
            await close_all_sessions()
        except Exception:
            pass
        InMemoryDataBridge.clear_dataset(did)


@router.delete("/delete")
async def delete_data(req: DatasetDeleteRequest,
                      db: SAGEDataStore = Depends(get_db)):
    """
        데이터셋 일괄 삭제 API
        - all: 전체 데이터셋 및 물리 디렉토리 삭제
        - exclude: 특정 did 배열을 제외한 모든 데이터셋 및 물리 디렉토리 삭제
        - list: 주어진 did 배열에 해당하는 데이터셋 및 물리 디렉토리 삭제
        """

    # 1. 모드별 타겟 did 목록 추출
    target_dids = []

    try:
        if req.mode == "all":
            # DB에 존재하는 모든 did 조회 (saged 내에 전체 did 리스트를 가져오는 메서드가 있다고 가정)
            target_dids = await saged.list_all_ids("did-")

        elif req.mode == "exclude":
            if not req.ids:
                raise HTTPException(status_code=400, detail="exclude 모드에서는 제외할 dids 배열이 필수입니다.")

            all_dids = await saged.list_all_ids("did-")
            # 입력받은 dids를 제외한 나머지 추출
            target_dids = [did for did in all_dids if did not in req.ids]

        elif req.mode == "list":
            if not req.ids:
                raise HTTPException(status_code=400, detail="list 모드에서는 삭제할 dids 배열이 필수입니다.")
            target_dids = req.ids

        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 mode 값입니다. ('all', 'exclude', 'list' 중 선택)")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 대상 식별 중 오류: {str(e)}")

    if not target_dids:
        return {"status": "success", "message": "삭제할 대상 데이터셋이 없습니다.", "deleted_count": 0}

    # 2. 루프를 돌며 DB 메타데이터 및 물리 파일 삭제 진행
    success_dids = []
    failed_dids = []

    for did in target_dids:
        try:
            # DB 삭제 확인
            await saged.delete(did)
            # if not success:
            #     # DB에 없는 경우 실패 목록에 추가하고 스킵
            #     failed_dids.append({"did": did, "reason": "DB에 존재하지 않음"})
            #     continue

            # 물리적 경로 설정 및 삭제
            target_dir = cfg.root_path / Path(f"data/{did}")

            if target_dir.exists() and target_dir.is_dir():
                if cfg.root_path in target_dir.parents:
                    shutil.rmtree(target_dir)

            success_dids.append(did)

        except Exception as e:
            print(f"did {did} 삭제 중 에러 발생")
            print(traceback.format_exc())
            failed_dids.append({"did": did, "reason": str(e)})

    # 3. 결과 반환
    return {
        "status": "partial_success" if failed_dids else "success",
        "mode": req.mode,
        "total_requested": len(target_dids),
        "deleted_count": len(success_dids),
        "success_dids": success_dids,
        "failed_dids": failed_dids
    }

    # """
    # 데이터셋 삭제: DB 메타데이터 삭제 후 물리적 파일 디렉토리 제거
    # """
    # # 1. DB에서 데이터 존재 여부 확인 및 삭제 실행
    # # (이미 saged.delete 내에서 존재 여부를 체크하여 deleted_count를 반환함)
    # success = await saged.delete(did)
    #
    # if not success:
    #     raise HTTPException(status_code=404, detail="삭제할 데이터셋이 DB에 존재하지 않습니다.")
    #
    # # 2. 물리적 경로 설정 및 삭제
    # # did 단위 폴더 전체를 삭제 타겟으로 설정
    # target_dir = cfg.root_path / Path(f"data/{did}")
    #
    # try:
    #     if target_dir.exists() and target_dir.is_dir():
    #         # 안전장치: cfg.root_path를 벗어난 경로인지 체크
    #         if cfg.root_path in target_dir.parents:
    #             # 디렉토리와 내부 파일 전체 삭제
    #             shutil.rmtree(target_dir)
    #         else:
    #             # 비정상적인 경로 접근 시 에러 (보안)
    #             raise HTTPException(status_code=400, detail="유효하지 않은 삭제 경로입니다.")
    #
    #     # 3. 결과 반환 (Pydantic 모델 없이 dict 직접 반환)
    #     return {
    #         "status": "success",
    #         "did": did,
    #     }
    #
    # except Exception as e:
    #     # 파일 삭제 중 오류 발생 시
    #     import traceback
    #     print(traceback.format_exc())
    #     raise HTTPException(status_code=500, detail=f"물리 파일 삭제 중 오류: {str(e)}")
