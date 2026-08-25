"""Common code (group/detail) admin API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from routers.base import APIResponse
from sage.admin.auth import get_current_user
from sage.admin.repository import AdminRepository
from sage.db import SAGEDataStore, get_db
from sage.logg import LoggingRoute, error
from sage.models.admin import AdminUser, CodeDetail, CodeDetailInfo, CodeGroup, CodeGroupInfo
from sage.admin.code_validators import validate_code, validate_detail_name, validate_group_name
from sage.models.admin_req import (
    CodeDetailDeleteRequest,
    CodeDetailListRequest,
    CodeDetailRegisterRequest,
    CodeDetailUpdateRequest,
    CodeGroupDeleteRequest,
    CodeGroupListRequest,
    CodeGroupRegisterRequest,
    CodeGroupUpdateRequest,
)

router = APIRouter(prefix="/admin/code", tags=["admin-code"], route_class=LoggingRoute)


def _group_info(g: CodeGroup) -> CodeGroupInfo:
    return CodeGroupInfo(
        group_code=g.group_code,
        group_name=g.group_name,
        description=g.description,
        use_yn=g.use_yn,
        created_at=g.created_at.isoformat() if g.created_at else None,
        updated_at=g.updated_at.isoformat() if g.updated_at else None,
    )


def _detail_info(d: CodeDetail) -> CodeDetailInfo:
    return CodeDetailInfo(
        detail_id=d.detail_id,
        group_code=d.group_code,
        code=d.code,
        name=d.name,
        sort_order=d.sort_order,
        use_yn=d.use_yn,
        created_at=d.created_at.isoformat() if d.created_at else None,
        updated_at=d.updated_at.isoformat() if d.updated_at else None,
    )


@router.post("/group/list", response_model=APIResponse[list[CodeGroupInfo]])
async def list_groups(
    req: CodeGroupListRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        groups = await repo.list_code_groups()
        if req.search:
            q = req.search.lower()
            groups = [g for g in groups if q in g.group_code.lower() or q in g.group_name.lower()]
        return APIResponse(success=True, result=[_group_info(g) for g in groups])
    except Exception as exc:
        error(f"list_groups failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.post("/group/register", response_model=APIResponse[CodeGroupInfo])
async def register_group(
    req: CodeGroupRegisterRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        code = req.group_code.strip()
        if err := validate_code(code, label="그룹코드"):
            return APIResponse(success=False, error=err)
        if err := validate_group_name(req.group_name):
            return APIResponse(success=False, error=err)
        if await repo.get_code_group(code):
            return APIResponse(success=False, error="이미 존재하는 그룹코드입니다.")
        now = datetime.now(timezone.utc)
        group = CodeGroup(
            group_code=code,
            group_name=req.group_name.strip(),
            description=req.description.strip(),
            created_at=now,
            updated_at=now,
        )
        saved = await repo.save_code_group(group)
        return APIResponse(success=True, result=_group_info(saved))
    except Exception as exc:
        error(f"register_group failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.put("/group/update", response_model=APIResponse[CodeGroupInfo])
async def update_group(
    req: CodeGroupUpdateRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        existing = await repo.get_code_group(req.group_code)
        if not existing:
            return APIResponse(success=False, error="그룹을 찾을 수 없습니다.")
        if err := validate_group_name(req.group_name):
            return APIResponse(success=False, error=err)
        existing.group_name = req.group_name.strip()
        existing.description = req.description.strip()
        existing.use_yn = req.use_yn
        saved = await repo.save_code_group(existing)
        return APIResponse(success=True, result=_group_info(saved))
    except Exception as exc:
        error(f"update_group failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.delete("/group/delete", response_model=APIResponse[dict])
async def delete_group(
    req: CodeGroupDeleteRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        await repo.delete_code_group(req.group_code)
        return APIResponse(success=True, result={"group_code": req.group_code})
    except ValueError as exc:
        return APIResponse(success=False, error=str(exc))
    except Exception as exc:
        error(f"delete_group failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.post("/detail/list", response_model=APIResponse[list[CodeDetailInfo]])
async def list_details(
    req: CodeDetailListRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        details = await repo.list_code_details(req.group_code)
        return APIResponse(success=True, result=[_detail_info(d) for d in details])
    except Exception as exc:
        error(f"list_details failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.post("/detail/register", response_model=APIResponse[CodeDetailInfo])
async def register_detail(
    req: CodeDetailRegisterRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        code = req.code.strip()
        if err := validate_code(code, label="코드"):
            return APIResponse(success=False, error=err)
        if err := validate_detail_name(req.name):
            return APIResponse(success=False, error=err)
        if await repo.get_code_detail(req.group_code, code):
            return APIResponse(success=False, error="같은 그룹에 이미 존재하는 코드입니다.")
        now = datetime.now(timezone.utc)
        detail = CodeDetail(
            detail_id=CodeDetail.make_id(req.group_code, code),
            group_code=req.group_code.strip(),
            code=code,
            name=req.name.strip(),
            sort_order=req.sort_order,
            created_at=now,
            updated_at=now,
        )
        saved = await repo.save_code_detail(detail)
        return APIResponse(success=True, result=_detail_info(saved))
    except ValueError as exc:
        return APIResponse(success=False, error=str(exc))
    except Exception as exc:
        error(f"register_detail failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.put("/detail/update", response_model=APIResponse[CodeDetailInfo])
async def update_detail(
    req: CodeDetailUpdateRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        existing = await repo.get_code_detail(req.group_code, req.code)
        if not existing:
            return APIResponse(success=False, error="상세 코드를 찾을 수 없습니다.")
        if err := validate_detail_name(req.name):
            return APIResponse(success=False, error=err)
        existing.name = req.name.strip()
        existing.sort_order = req.sort_order
        existing.use_yn = req.use_yn
        saved = await repo.save_code_detail(existing)
        return APIResponse(success=True, result=_detail_info(saved))
    except Exception as exc:
        error(f"update_detail failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.delete("/detail/delete", response_model=APIResponse[dict])
async def delete_detail(
    req: CodeDetailDeleteRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        await repo.delete_code_detail(req.group_code, req.code)
        return APIResponse(success=True, result={"group_code": req.group_code, "code": req.code})
    except Exception as exc:
        error(f"delete_detail failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.post("/detail/lookup", response_model=APIResponse[list[CodeDetailInfo]])
async def lookup_details(
    req: CodeDetailListRequest,
    db: SAGEDataStore = Depends(get_db),
):
    """공개 lookup — Data/Tool category 드롭다운용 (인증 생략)."""
    try:
        repo = AdminRepository(db)
        details = await repo.list_code_details(req.group_code)
        active = [d for d in details if d.use_yn]
        return APIResponse(success=True, result=[_detail_info(d) for d in active])
    except Exception as exc:
        error(f"lookup_details failed: {exc}")
        return APIResponse(success=False, error=str(exc))
