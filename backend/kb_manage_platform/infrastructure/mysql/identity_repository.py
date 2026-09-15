"""使用 SQLAlchemy 读取用户、部门和角色上下文。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.domain.models import UserContext
from kb_manage_platform.infrastructure.mysql.models import (
    DepartmentModel,
    RoleModel,
    RolePermissionModel,
    UserModel,
    UserRoleModel,
)


class MysqlIdentityRepository:
    """MySQL 身份上下文仓储。"""

    # 作用：保存异步会话工厂。
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：按用户 ID 获取可信身份、部门和角色上下文。
    async def get_user_context(self, user_id: str) -> UserContext:
        """返回用户权限上下文。"""
        async with self._session_factory() as session:
            user = await session.get(UserModel, user_id)
            if user is None:
                raise LookupError(f"user not found: {user_id}")
            department = await session.get(DepartmentModel, user.department_id)
            role_ids = tuple(
                (
                    await session.scalars(
                        select(UserRoleModel.role_id)
                        .join(RoleModel, RoleModel.role_id == UserRoleModel.role_id)
                        .where(
                            UserRoleModel.user_id == user_id,
                            RoleModel.status == "active",
                        )
                    )
                ).all()
            )
            permission_codes = tuple(
                (
                    await session.scalars(
                        select(RolePermissionModel.permission_code)
                        .join(RoleModel, RoleModel.role_id == RolePermissionModel.role_id)
                        .where(
                            RolePermissionModel.role_id.in_(role_ids),
                            RoleModel.status == "active",
                        )
                    )
                ).all()
            )
        department_path = tuple(part for part in (department.path.split("/") if department else []) if part)
        return UserContext(
            user_id=user.user_id,
            department_id=user.department_id,
            department_path=department_path,
            role_ids=role_ids,
            permission_version=user.permission_version,
            is_active=user.status == "active",
            permission_codes=permission_codes,
        )