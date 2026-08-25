"""Seed admin settings initial data."""

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from sage.admin.passwords import hash_password
from sage.admin.repository import AdminRepository
from sage.db import saged
from sage.models.admin import AdminUser, CodeDetail, CodeGroup


async def seed() -> None:
    repo = AdminRepository(saged)

    admin_login = os.environ.get("SAGE_ADMIN_LOGIN_ID", "admin")
    admin_password = os.environ.get("SAGE_ADMIN_PASSWORD", "admin")

    if not await repo.get_user_by_login_id(admin_login):
        await repo.save_user(
            AdminUser(
                user_id=AdminUser.make_id(),
                login_id=admin_login,
                name="시스템 관리자",
                email="admin@sage.local",
                password_hash=hash_password(admin_password),
                role="admin",
            )
        )
        print(f"Created admin user: {admin_login}")

    groups = [
        ("Category", "카테고리"),
        ("SRC_TYPE", "데이터 소스 유형"),
        ("STATUS", "처리 상태"),
    ]
    for code, name in groups:
        if not await repo.get_code_group(code):
            await repo.save_code_group(CodeGroup(group_code=code, group_name=name))

    details = [
        ("Category", "FIN", "재무", 1),
        ("Category", "SALES", "영업", 2),
        ("Category", "OPS", "운영", 3),
        ("SRC_TYPE", "FILE", "파일", 1),
        ("SRC_TYPE", "DB", "DB", 2),
        ("SRC_TYPE", "TOOL", "도구", 3),
        ("STATUS", "READY", "대기", 1),
        ("STATUS", "DONE", "완료", 2),
    ]
    for group_code, code, name, sort_order in details:
        if not await repo.get_code_detail(group_code, code):
            await repo.save_code_detail(
                CodeDetail(
                    detail_id=CodeDetail.make_id(group_code, code),
                    group_code=group_code,
                    code=code,
                    name=name,
                    sort_order=sort_order,
                )
            )

    print("Admin seed completed.")


if __name__ == "__main__":
    asyncio.run(seed())
