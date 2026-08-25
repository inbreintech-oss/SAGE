"""Admin user management API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from routers.base import APIResponse
from sage.admin.auth import get_current_user
from sage.admin.passwords import hash_password
from sage.admin.repository import AdminRepository
from sage.db import SAGEDataStore, get_db
from sage.logg import LoggingRoute, error
from sage.models.admin import AdminUser, AdminUserPublic
from sage.models.admin_req import (
    AdminCheckEmailRequest,
    AdminCheckIdRequest,
    AdminUserDeleteRequest,
    AdminUserListRequest,
    AdminUserRegisterRequest,
    AdminUserUpdateRequest,
)

router = APIRouter(prefix="/admin/user", tags=["admin-user"], route_class=LoggingRoute)


def _public(user: AdminUser) -> AdminUserPublic:
    return AdminUserPublic(
        user_id=user.user_id,
        login_id=user.login_id,
        name=user.name,
        email=user.email,
        role=user.role,
        disabled=user.disabled,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.post("/list", response_model=APIResponse[list[AdminUserPublic]])
async def list_users(
    req: AdminUserListRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        users = await repo.list_users(req.search)
        return APIResponse(success=True, result=[_public(u) for u in users])
    except Exception as exc:
        error(f"list_users failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.post("/register", response_model=APIResponse[AdminUserPublic])
async def register_user(
    req: AdminUserRegisterRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        login_id = req.login_id.strip()
        if await repo.get_user_by_login_id(login_id):
            return APIResponse(success=False, error="이미 사용 중인 ID입니다.")
        now = datetime.now(timezone.utc)
        user = AdminUser(
            user_id=AdminUser.make_id(),
            login_id=login_id,
            name=req.name.strip(),
            email=req.email.strip(),
            password_hash=hash_password(req.password),
            role=req.role,
            created_at=now,
            updated_at=now,
        )
        saved = await repo.save_user(user)
        return APIResponse(success=True, result=_public(saved))
    except Exception as exc:
        error(f"register_user failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.put("/update", response_model=APIResponse[AdminUserPublic])
async def update_user(
    req: AdminUserUpdateRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        existing = await repo.get_user(req.user_id)
        if not existing:
            return APIResponse(success=False, error="사용자를 찾을 수 없습니다.")
        existing.name = req.name.strip()
        existing.email = req.email.strip()
        existing.role = req.role
        existing.disabled = req.disabled
        if req.password:
            existing.password_hash = hash_password(req.password)
        saved = await repo.save_user(existing)
        return APIResponse(success=True, result=_public(saved))
    except Exception as exc:
        error(f"update_user failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.delete("/delete", response_model=APIResponse[dict])
async def delete_user(
    req: AdminUserDeleteRequest,
    db: SAGEDataStore = Depends(get_db),
    current: AdminUser = Depends(get_current_user),
):
    try:
        if req.user_id == current.user_id:
            return APIResponse(success=False, error="현재 로그인 사용자는 삭제할 수 없습니다.")
        repo = AdminRepository(db)
        await repo.delete_user(req.user_id)
        return APIResponse(success=True, result={"user_id": req.user_id})
    except Exception as exc:
        error(f"delete_user failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.post("/check-id", response_model=APIResponse[dict])
async def check_login_id(
    req: AdminCheckIdRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    repo = AdminRepository(db)
    exists = await repo.get_user_by_login_id(req.login_id.strip()) is not None
    return APIResponse(success=True, result={"available": not exists})


@router.post("/check-email", response_model=APIResponse[dict])
async def check_email(
    req: AdminCheckEmailRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    repo = AdminRepository(db)
    email = req.email.strip().lower()
    users = await repo.list_users()
    taken = any(
        u.email.lower() == email and u.user_id != req.exclude_user_id
        for u in users
        if u.email
    )
    return APIResponse(success=True, result={"available": not taken})
