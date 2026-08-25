"""SecretKey 등록·조회 API."""

from datetime import datetime, timezone
import shutil
import traceback

from fastapi import APIRouter, Depends, HTTPException, Query

import cfg
from routers.base import APIResponse, DeleteResponse
from sage.db import SAGEDataStore, get_db
from sage.logg import LoggingRoute, error
from sage.models import doc
from sage.models.doc import KeyItem
from sage.models.req import KeyDeleteRequest, ListKeysRequest, RegisterKeyRequest, SecretKeyInfo, RegisteredKeyName
from sage.secret.crypto import encrypt_api_key, normalize_key_name

router = APIRouter(
    prefix="/secret",
    tags=["secret"],
    route_class=LoggingRoute,
)


def _to_info(record: doc.SecretKey) -> SecretKeyInfo:
    # 민감한 값(key_value)은 빼고 key_name만 응답에 포함
    registered_keys = [
        RegisteredKeyName(key_name=item.key_name)
        for item in record.keys
    ]

    return SecretKeyInfo(
        secret_id=record.secret_id,
        user_id=record.user_id,
        provider=record.provider,
        keys=registered_keys,
        description=record.description,
        created_at=record.created_at.isoformat() if record.created_at else None,
        updated_at=record.updated_at.isoformat() if record.updated_at else None,
    )


@router.post("/register", response_model=APIResponse[SecretKeyInfo])
async def register_key(req: RegisterKeyRequest, db: SAGEDataStore = Depends(get_db)):
    """user_id와 provider 단위로 여러 키(KeyItem)를 암호화하여 하나의 SecretKey 문서로 저장."""
    try:
        now = datetime.now(timezone.utc)

        # 1. provider 기반 고유 ID 생성
        secret_id = doc.SecretKey.make_id()

        # 2. 요청된 모든 키 목록을 순회하며 key_name 정규화 및 value 암호화
        encrypted_keys = []
        for item in req.keys:
            key_name = normalize_key_name(item.key_name)
            encrypted_value = encrypt_api_key(item.key_value)

            encrypted_keys.append(
                KeyItem(key_name=key_name, key_value=encrypted_value)
            )

        # 3. 기존 문서 로드 (생성일 유지를 위함)
        existing = await db.load(doc.SecretKey, secret_id)

        # 4. 새 레코드 생성 (하나의 문서에 keys 리스트 주입)
        record = doc.SecretKey(
            secret_id=secret_id,
            user_id=req.user_id,
            provider=req.provider,
            keys=encrypted_keys,
            description=req.description,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )

        await db.save(record)
        return APIResponse(success=True, result=_to_info(record))

    except Exception as e:
        error(f"register_key failed: {e}")
        return APIResponse(success=False, error=str(e))


# def _list_keys_params(
#     user_id: str = Query(default="admin", description="조회 user_id"),
# ) -> ListKeysRequest:
#     return ListKeysRequest(user_id=user_id)


@router.post("/list", response_model=APIResponse[list[SecretKeyInfo]])
async def list_keys(
    req: ListKeysRequest,
    db: SAGEDataStore = Depends(get_db),
):
    """SecretKey 목록 (api_key 값은 반환하지 않음)."""
    try:
        records = await db.list_secrets(req.user_id)
        return APIResponse(success=True, result=[_to_info(r) for r in records])
    except Exception as e:
        error(f"list_keys failed: {e}")
        return APIResponse(success=False, error=str(e))


@router.delete("/delete", response_model=DeleteResponse)
async def delete_keys(
        req: KeyDeleteRequest,
        saged: SAGEDataStore = Depends(get_db)
):
    """
    도구 일괄 삭제 API
    - all: 전체 도구 레코드 및 물리 디렉토리 삭제
    - exclude: 특정 tool_id 배열을 제외한 모든 도구 레코드 및 물리 디렉토리 삭제
    - list: 주어진 tool_id 배열에 해당하는 도구 레코드 및 물리 디렉토리 삭제
    """

    # 1. 모드별 타겟 tool_id 목록 추출
    target_secret_key_ids = []

    try:
        if req.mode == "all":
            # tm- 접두사를 활용하여 전체 도구 ID 목록 조회
            target_secret_key_ids = await saged.list_all_ids("sk-")

        elif req.mode == "exclude":
            if not req.ids:
                raise HTTPException(status_code=400, detail="exclude 모드에서는 제외할 tool_ids 배열이 필수입니다.")

            all_tool_ids = await saged.list_all_ids("sk-")
            exclude_set = set(req.ids)
            target_secret_key_ids = [tid for tid in all_tool_ids if tid not in exclude_set]

        elif req.mode == "list":
            if not req.ids:
                raise HTTPException(status_code=400, detail="list 모드에서는 삭제할 tool_ids 배열이 필수입니다.")
            target_secret_key_ids = req.ids

        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 mode 값입니다. ('all', 'exclude', 'list' 중 선택)")

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 대상 식별 중 오류: {str(e)}")

    if not target_secret_key_ids:
        return DeleteResponse(
            status="success",
            id=str(req.ids or []),
            message="삭제할 대상 도구가 없습니다."
        )

    # 2. 루프를 돌며 DB 메타데이터 및 물리 파일(tools/{tool_id}) 삭제 진행
    success_tids = []
    failed_tids = []

    for secret_id in target_secret_key_ids:
        try:
            # 2-1. 데이터베이스(doc.Tool) 삭제
            await saged.delete(secret_id)

        except Exception as e:
            print(f"secret_id {secret_id} 및 물리 파일 삭제 중 에러 발생")
            print(traceback.format_exc())
            failed_tids.append({"secret_id": secret_id, "reason": str(e)})

    # 3. 결과 반환
    status_str = "partial_success" if failed_tids else "success"

    return DeleteResponse(
        status=status_str,
        id=str(req.ids or []),
        message=f"요청된 대상 중 {len(success_tids)}개의 도구 레코드 및 물리 폴더가 삭제되었습니다."
    )