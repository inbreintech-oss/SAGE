"""Admin settings domain models (users, common codes, API orgs)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AdminUserRole = Literal["admin", "member"]


class CodeGroup(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    group_code: str = Field(description="그룹 코드 PK (= MongoDB _id)")
    group_name: str = Field(description="그룹코드명")
    description: str = Field(default="", description="설명")
    use_yn: bool = Field(default=True, description="사용 여부")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CodeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detail_id: str = Field(description="복합 PK group_code:code (= MongoDB _id)")
    group_code: str = Field(description="FK → code_groups.group_code")
    code: str = Field(description="상세 코드")
    name: str = Field(description="명칭")
    sort_order: int = Field(default=1, description="정렬순서")
    use_yn: bool = Field(default=True, description="사용 여부")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def make_id(cls, group_code: str, code: str) -> str:
        return f"{group_code}:{code}"


class AdminUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str = Field(description="usr-{uuid} (= MongoDB _id)")
    login_id: str = Field(description="로그인 ID")
    name: str = Field(description="사용자명")
    email: str = Field(default="", description="이메일")
    password_hash: str = Field(description="비밀번호 해시")
    role: AdminUserRole = Field(default="member")
    disabled: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def make_id(cls) -> str:
        return f"usr-{uuid.uuid4().hex}"


class ApiOrganization(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: str = Field(description="org-{uuid} (= MongoDB _id)")
    name: str = Field(description="기관명")
    code: str = Field(description="기관코드")
    base_url: str = Field(default="", description="기본 URL")
    secret_id: str = Field(default="", description="연결 SecretKey (sk-*)")
    description: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def make_id(cls) -> str:
        return f"org-{uuid.uuid4().hex}"


class AdminUserPublic(BaseModel):
    user_id: str
    login_id: str
    name: str
    email: str
    role: AdminUserRole
    disabled: bool
    created_at: str | None = None
    updated_at: str | None = None


class CodeGroupInfo(BaseModel):
    group_code: str
    group_name: str
    description: str = ""
    use_yn: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class CodeDetailInfo(BaseModel):
    detail_id: str
    group_code: str
    code: str
    name: str
    sort_order: int
    use_yn: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class ApiOrgKeyInfo(BaseModel):
    key_name: str
    value_masked: str = "••••"


class ApiOrganizationInfo(BaseModel):
    org_id: str
    name: str
    code: str
    base_url: str
    secret_id: str
    description: str = ""
    auth_keys: list[ApiOrgKeyInfo] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
