"""幂等初始化管理员、角色映射和阶段 A 演示数据。"""

import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert

from kb_manage_platform.bootstrap.schema_check import check_schema
from kb_manage_platform.bootstrap.settings import get_settings
from kb_manage_platform.infrastructure.adapters.security_utils import ScryptPasswordHasher
from kb_manage_platform.infrastructure.mysql.models import (
    DepartmentModel,
    KnowledgePermissionModel,
    KnowledgeUnitModel,
    QaAuditModel,
    RoleModel,
    UserModel,
    UserRoleModel,
)
from kb_manage_platform.infrastructure.mysql.session import Database


async def seed() -> None:
    """写入可重复执行的初始数据。"""
    settings = get_settings()
    if not settings.seed_admin_password or settings.seed_admin_password.startswith("CHANGE_ME"):
        raise RuntimeError("SEED_ADMIN_PASSWORD must be configured before seeding")
    hasher = ScryptPasswordHasher()
    database = Database(settings.mysql_dsn(), pool_size=2)
    try:
        await check_schema(database)
        async with database.session_factory() as session:
            await _seed_departments(session)
            await _seed_admin(session, settings.seed_admin_username, hasher.hash(settings.seed_admin_password))
            if settings.seed_demo_data:
                await _seed_demo_accounts(session, settings.seed_admin_password, hasher)
                await _seed_demo_knowledge(session)
                await _seed_dashboard_baseline(session)
            await session.commit()
    finally:
        await database.dispose()


async def _seed_departments(session) -> None:
    rows = [
        {"department_id": "dept-root", "name": "总公司", "parent_id": "", "path": "dept-root", "status": "active"},
        {"department_id": "dept-hr", "name": "人力资源部", "parent_id": "dept-root", "path": "dept-root/dept-hr", "status": "active"},
        {"department_id": "dept-product", "name": "产品研发部", "parent_id": "dept-root", "path": "dept-root/dept-product", "status": "active"},
    ]
    for row in rows:
        await session.execute(insert(DepartmentModel).prefix_with("IGNORE").values(**row))


async def _seed_admin(session, username: str, password_hash: str) -> None:
    statement = insert(UserModel).prefix_with("IGNORE").values(
        user_id="user-admin",
        username=username,
        department_id="dept-root",
        status="active",
        permission_version=1,
        password_hash=password_hash,
    )
    await session.execute(statement)
    role_exists = await session.scalar(
        select(RoleModel.role_id).where(RoleModel.role_id == "role-system-admin")
    )
    if role_exists:
        await session.execute(
            insert(UserRoleModel)
            .prefix_with("IGNORE")
            .values(user_id="user-admin", role_id="role-system-admin")
        )


async def _seed_demo_accounts(session, password: str, hasher: ScryptPasswordHasher) -> None:
    accounts = [
        ("user-kbadmin", "kbadmin", "dept-product", "role-knowledge-admin"),
        ("user-demo", "demo", "dept-product", "role-user"),
    ]
    for user_id, username, department_id, role_id in accounts:
        await session.execute(
            insert(UserModel)
            .prefix_with("IGNORE")
            .values(
                user_id=user_id,
                username=username,
                department_id=department_id,
                status="active",
                permission_version=1,
                password_hash=hasher.hash(password),
            )
        )
        await session.execute(
            insert(UserRoleModel).prefix_with("IGNORE").values(user_id=user_id, role_id=role_id)
        )


async def _seed_demo_knowledge(session) -> None:
    await session.execute(
        insert(KnowledgeUnitModel)
        .prefix_with("IGNORE")
        .values(
            knowledge_id="knowledge-demo-travel",
            title="差旅报销示例知识",
            category_id="finance-travel",
            tags=["财务", "差旅", "示例"],
            status="draft",
            current_version_id=None,
            created_by="user-kbadmin",
            updated_by="user-kbadmin",
        )
    )
    await session.execute(
        insert(KnowledgePermissionModel)
        .prefix_with("IGNORE")
        .values(
            knowledge_id="knowledge-demo-travel",
            scope="user",
            subject_id="user-kbadmin",
            include_descendants=False,
            permission_version=1,
            created_by="user-kbadmin",
            updated_by="user-kbadmin",
        )
    )


async def _seed_dashboard_baseline(session) -> None:
    exists = await session.scalar(
        select(QaAuditModel.id).where(QaAuditModel.request_id == "demo-metrics-1").limit(1)
    )
    if exists:
        return
    session.add(
        QaAuditModel(
            event_type="qa.metrics",
            request_id="demo-metrics-1",
            user_id="user-demo",
            payload={
                "request_id": "demo-metrics-1",
                "user_id": "user-demo",
                "latency_ms": 820.0,
                "estimated_tokens": 280,
                "demo": True,
            },
        )
    )


if __name__ == "__main__":
    asyncio.run(seed())





