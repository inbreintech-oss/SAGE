"""Admin API request/response DTOs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sage.models.admin import AdminUserRole
from sage.models.doc import KeyItem


class AdminLoginRequest(BaseModel):
    login_id: str
    password: str


class AdminPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class CodeGroupListRequest(BaseModel):
    search: str | None = None


class CodeGroupRegisterRequest(BaseModel):
    group_code: str
    group_name: str
    description: str = ""


class CodeGroupUpdateRequest(BaseModel):
    group_code: str
    group_name: str
    description: str = ""
    use_yn: bool = True


class CodeGroupDeleteRequest(BaseModel):
    group_code: str


class CodeDetailListRequest(BaseModel):
    group_code: str


class CodeDetailRegisterRequest(BaseModel):
    group_code: str
    code: str
    name: str
    sort_order: int = 1


class CodeDetailUpdateRequest(BaseModel):
    group_code: str
    code: str
    name: str
    sort_order: int = 1
    use_yn: bool = True


class CodeDetailDeleteRequest(BaseModel):
    group_code: str
    code: str


class AdminUserListRequest(BaseModel):
    search: str | None = None


class AdminUserRegisterRequest(BaseModel):
    login_id: str
    name: str
    email: str = ""
    password: str
    role: AdminUserRole = "member"


class AdminUserUpdateRequest(BaseModel):
    user_id: str
    name: str
    email: str = ""
    password: str | None = None
    role: AdminUserRole = "member"
    disabled: bool = False


class AdminUserDeleteRequest(BaseModel):
    user_id: str


class AdminCheckIdRequest(BaseModel):
    login_id: str


class AdminCheckEmailRequest(BaseModel):
    email: str
    exclude_user_id: str | None = None


class ApiOrgListRequest(BaseModel):
    pass


class ApiOrgRegisterRequest(BaseModel):
    name: str
    code: str
    base_url: str = ""
    description: str = ""
    keys: list[KeyItem] = Field(default_factory=list)


class ApiOrgUpdateRequest(BaseModel):
    org_id: str
    name: str
    code: str
    base_url: str = ""
    description: str = ""
    keys: list[KeyItem] = Field(default_factory=list)


class ApiOrgDeleteRequest(BaseModel):
    org_id: str


class AdminDeleteModeRequest(BaseModel):
    mode: Literal["list"] = "list"
    ids: list[str] = Field(default_factory=list)
