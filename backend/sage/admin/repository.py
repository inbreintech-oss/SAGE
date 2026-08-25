"""MongoDB repository for admin settings collections."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sage.db.store import SAGEDataStore, universal_serializer
from sage.models.admin import AdminUser, ApiOrganization, CodeDetail, CodeGroup


COL_CODE_GROUPS = "code_groups"
COL_CODE_DETAILS = "code_details"
COL_ADMIN_USERS = "admin_users"
COL_API_ORGS = "api_orgs"


class AdminRepository:
    def __init__(self, store: SAGEDataStore):
        self._store = store
        self._backend = store._backend

    async def _replace(self, collection: str, doc_id: str, model) -> None:
        raw = universal_serializer(model)
        raw["_id"] = doc_id
        raw["updated_at"] = datetime.now(timezone.utc)
        await self._backend.replace_one(collection, doc_id, raw)

    async def _find_one(self, collection: str, doc_id: str) -> dict[str, Any] | None:
        raw = await self._backend.find_one(collection, {"_id": doc_id})
        return self._store._read(raw) if raw else None

    async def _find_many(
        self,
        collection: str,
        filter_query: dict | None = None,
        *,
        sort: list | None = None,
    ) -> list[dict[str, Any]]:
        docs = await self._backend.find_many(collection, filter_query or {}, sort=sort)
        return [self._store._read(d) for d in docs]

    # --- code groups ---

    async def list_code_groups(self) -> list[CodeGroup]:
        rows = await self._find_many(COL_CODE_GROUPS, sort=[("group_code", 1)])
        return [CodeGroup.model_validate(r) for r in rows]

    async def get_code_group(self, group_code: str) -> CodeGroup | None:
        raw = await self._find_one(COL_CODE_GROUPS, group_code)
        return CodeGroup.model_validate(raw) if raw else None

    async def save_code_group(self, group: CodeGroup) -> CodeGroup:
        existing = await self.get_code_group(group.group_code)
        if existing:
            group.created_at = existing.created_at
        group.updated_at = datetime.now(timezone.utc)
        await self._replace(COL_CODE_GROUPS, group.group_code, group)
        return group

    async def delete_code_group(self, group_code: str) -> int:
        details = await self.list_code_details(group_code)
        if details:
            raise ValueError("하위 상세 코드가 있어 그룹을 삭제할 수 없습니다.")
        return await self._backend.delete_one(COL_CODE_GROUPS, group_code)

    # --- code details ---

    async def list_code_details(self, group_code: str | None = None) -> list[CodeDetail]:
        filt = {"group_code": group_code} if group_code else {}
        rows = await self._find_many(
            COL_CODE_DETAILS,
            filt,
            sort=[("group_code", 1), ("sort_order", 1), ("code", 1)],
        )
        return [CodeDetail.model_validate(r) for r in rows]

    async def get_code_detail(self, group_code: str, code: str) -> CodeDetail | None:
        detail_id = CodeDetail.make_id(group_code, code)
        raw = await self._find_one(COL_CODE_DETAILS, detail_id)
        return CodeDetail.model_validate(raw) if raw else None

    async def save_code_detail(self, detail: CodeDetail) -> CodeDetail:
        if not await self.get_code_group(detail.group_code):
            raise ValueError(f"그룹 코드 '{detail.group_code}' 가 존재하지 않습니다.")
        detail.detail_id = CodeDetail.make_id(detail.group_code, detail.code)
        existing = await self._find_one(COL_CODE_DETAILS, detail.detail_id)
        if existing:
            detail.created_at = CodeDetail.model_validate(existing).created_at
        detail.updated_at = datetime.now(timezone.utc)
        await self._replace(COL_CODE_DETAILS, detail.detail_id, detail)
        return detail

    async def delete_code_detail(self, group_code: str, code: str) -> int:
        detail_id = CodeDetail.make_id(group_code, code)
        return await self._backend.delete_one(COL_CODE_DETAILS, detail_id)

    # --- users ---

    async def list_users(self, search: str | None = None) -> list[AdminUser]:
        rows = await self._find_many(COL_ADMIN_USERS, sort=[("login_id", 1)])
        users = [AdminUser.model_validate(r) for r in rows]
        if not search:
            return users
        q = search.lower()
        return [
            u for u in users
            if q in u.login_id.lower() or q in u.name.lower() or q in u.email.lower()
        ]

    async def get_user(self, user_id: str) -> AdminUser | None:
        raw = await self._find_one(COL_ADMIN_USERS, user_id)
        return AdminUser.model_validate(raw) if raw else None

    async def get_user_by_login_id(self, login_id: str) -> AdminUser | None:
        raw = await self._backend.find_one(COL_ADMIN_USERS, {"login_id": login_id})
        data = self._store._read(raw) if raw else None
        return AdminUser.model_validate(data) if data else None

    async def save_user(self, user: AdminUser) -> AdminUser:
        existing = await self.get_user(user.user_id)
        if existing:
            user.created_at = existing.created_at
        user.updated_at = datetime.now(timezone.utc)
        await self._replace(COL_ADMIN_USERS, user.user_id, user)
        return user

    async def delete_user(self, user_id: str) -> int:
        return await self._backend.delete_one(COL_ADMIN_USERS, user_id)

    # --- api orgs ---

    async def list_api_orgs(self) -> list[ApiOrganization]:
        rows = await self._find_many(COL_API_ORGS, sort=[("name", 1)])
        return [ApiOrganization.model_validate(r) for r in rows]

    async def get_api_org(self, org_id: str) -> ApiOrganization | None:
        raw = await self._find_one(COL_API_ORGS, org_id)
        return ApiOrganization.model_validate(raw) if raw else None

    async def save_api_org(self, org: ApiOrganization) -> ApiOrganization:
        existing = await self.get_api_org(org.org_id)
        if existing:
            org.created_at = existing.created_at
        org.updated_at = datetime.now(timezone.utc)
        await self._replace(COL_API_ORGS, org.org_id, org)
        return org

    async def delete_api_org(self, org_id: str) -> int:
        return await self._backend.delete_one(COL_API_ORGS, org_id)
