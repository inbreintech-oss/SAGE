"""API integration organization admin API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from routers.base import APIResponse
from sage.admin.auth import get_current_user
from sage.admin.repository import AdminRepository
from sage.db import SAGEDataStore, get_db
from sage.logg import LoggingRoute, error
from sage.models.admin import AdminUser, ApiOrganization, ApiOrganizationInfo, ApiOrgKeyInfo
from sage.models.admin_req import ApiOrgDeleteRequest, ApiOrgListRequest, ApiOrgRegisterRequest, ApiOrgUpdateRequest
from sage.models.doc import KeyItem, SecretKey
from sage.secret.crypto import encrypt_api_key, normalize_key_name

router = APIRouter(prefix="/admin/org", tags=["admin-org"], route_class=LoggingRoute)


def _mask_key_value(value: str) -> str:
    tail = value[-4:] if len(value) >= 4 else value
    return f"••••••••{tail}"


async def _org_info(db: SAGEDataStore, org: ApiOrganization) -> ApiOrganizationInfo:
    keys: list[ApiOrgKeyInfo] = []
    if org.secret_id:
        secret = await db.load(SecretKey, org.secret_id)
        if secret:
            for item in secret.keys:
                keys.append(ApiOrgKeyInfo(key_name=item.key_name, value_masked="••••"))
    return ApiOrganizationInfo(
        org_id=org.org_id,
        name=org.name,
        code=org.code,
        base_url=org.base_url,
        secret_id=org.secret_id,
        description=org.description,
        auth_keys=keys,
        created_at=org.created_at.isoformat() if org.created_at else None,
        updated_at=org.updated_at.isoformat() if org.updated_at else None,
    )


async def _save_secret(db: SAGEDataStore, org_code: str, keys: list[KeyItem], existing_secret_id: str | None) -> str:
    now = datetime.now(timezone.utc)
    secret_id = existing_secret_id or SecretKey.make_id()
    existing = await db.load(SecretKey, secret_id) if existing_secret_id else None

    encrypted_keys: list[KeyItem] = []
    if keys:
        for item in keys:
            if not item.key_name.strip():
                continue
            if item.key_value.strip():
                encrypted_keys.append(
                    KeyItem(
                        key_name=normalize_key_name(item.key_name),
                        key_value=encrypt_api_key(item.key_value),
                    )
                )
            elif existing:
                for old in existing.keys:
                    if old.key_name == normalize_key_name(item.key_name):
                        encrypted_keys.append(old)
                        break

    if not encrypted_keys and existing:
        encrypted_keys = existing.keys

    record = SecretKey(
        secret_id=secret_id,
        user_id="admin",
        provider=org_code,
        keys=encrypted_keys,
        description=f"API org {org_code}",
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )
    await db.save(record)
    return secret_id


@router.post("/list", response_model=APIResponse[list[ApiOrganizationInfo]])
async def list_orgs(
    req: ApiOrgListRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        orgs = await repo.list_api_orgs()
        result = [await _org_info(db, o) for o in orgs]
        return APIResponse(success=True, result=result)
    except Exception as exc:
        error(f"list_orgs failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.post("/register", response_model=APIResponse[ApiOrganizationInfo])
async def register_org(
    req: ApiOrgRegisterRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        now = datetime.now(timezone.utc)
        org_id = ApiOrganization.make_id()
        secret_id = await _save_secret(db, req.code.strip(), req.keys, None)
        org = ApiOrganization(
            org_id=org_id,
            name=req.name.strip(),
            code=req.code.strip(),
            base_url=req.base_url.strip(),
            secret_id=secret_id,
            description=req.description.strip(),
            created_at=now,
            updated_at=now,
        )
        saved = await repo.save_api_org(org)
        return APIResponse(success=True, result=await _org_info(db, saved))
    except Exception as exc:
        error(f"register_org failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.put("/update", response_model=APIResponse[ApiOrganizationInfo])
async def update_org(
    req: ApiOrgUpdateRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        existing = await repo.get_api_org(req.org_id)
        if not existing:
            return APIResponse(success=False, error="기관을 찾을 수 없습니다.")
        secret_id = await _save_secret(db, req.code.strip(), req.keys, existing.secret_id or None)
        existing.name = req.name.strip()
        existing.code = req.code.strip()
        existing.base_url = req.base_url.strip()
        existing.description = req.description.strip()
        existing.secret_id = secret_id
        saved = await repo.save_api_org(existing)
        return APIResponse(success=True, result=await _org_info(db, saved))
    except Exception as exc:
        error(f"update_org failed: {exc}")
        return APIResponse(success=False, error=str(exc))


@router.delete("/delete", response_model=APIResponse[dict])
async def delete_org(
    req: ApiOrgDeleteRequest,
    db: SAGEDataStore = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    try:
        repo = AdminRepository(db)
        org = await repo.get_api_org(req.org_id)
        if not org:
            return APIResponse(success=False, error="기관을 찾을 수 없습니다.")
        if org.secret_id:
            await db.delete(org.secret_id)
        await repo.delete_api_org(req.org_id)
        return APIResponse(success=True, result={"org_id": req.org_id})
    except Exception as exc:
        error(f"delete_org failed: {exc}")
        return APIResponse(success=False, error=str(exc))
