"""Admin authentication API."""

from fastapi import APIRouter, Depends, Response

from routers.base import APIResponse
from sage.admin.auth import COOKIE_NAME, create_access_token, get_current_user
from sage.admin.passwords import hash_password, verify_password
from sage.admin.repository import AdminRepository
from sage.db import SAGEDataStore, get_db
from sage.logg import LoggingRoute
from sage.models.admin import AdminUser, AdminUserPublic
from sage.models.admin_req import AdminLoginRequest, AdminPasswordChangeRequest

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"], route_class=LoggingRoute)


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


@router.post("/login", response_model=APIResponse[AdminUserPublic])
async def login(req: AdminLoginRequest, response: Response, db: SAGEDataStore = Depends(get_db)):
    repo = AdminRepository(db)
    user = await repo.get_user_by_login_id(req.login_id.strip())
    if not user or user.disabled or not verify_password(req.password, user.password_hash):
        return APIResponse(success=False, error="ID 또는 비밀번호가 올바르지 않습니다.")
    token = create_access_token(user)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )
    return APIResponse(success=True, result=_public(user))


@router.post("/logout", response_model=APIResponse[dict])
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return APIResponse(success=True, result={"message": "logged out"})


@router.post("/me", response_model=APIResponse[AdminUserPublic])
async def me(user: AdminUser = Depends(get_current_user)):
    return APIResponse(success=True, result=_public(user))


@router.post("/password", response_model=APIResponse[AdminUserPublic])
async def change_password(
    req: AdminPasswordChangeRequest,
    user: AdminUser = Depends(get_current_user),
    db: SAGEDataStore = Depends(get_db),
):
    if not verify_password(req.current_password, user.password_hash):
        return APIResponse(success=False, error="현재 비밀번호가 올바르지 않습니다.")
    if len(req.new_password) < 4:
        return APIResponse(success=False, error="새 비밀번호는 4자 이상이어야 합니다.")
    user.password_hash = hash_password(req.new_password)
    repo = AdminRepository(db)
    saved = await repo.save_user(user)
    return APIResponse(success=True, result=_public(saved))
