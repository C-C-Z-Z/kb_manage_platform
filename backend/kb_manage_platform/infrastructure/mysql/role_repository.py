"""使用 SQLAlchemy 管理角色和操作权限。"""

from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.common.errors import ConflictError, NotFoundError
from kb_manage_platform.domain.models import PermissionDefinition, Role
from kb_manage_platform.infrastructure.mysql.models import IamPermissionModel, RoleModel, RolePermissionModel, UserModel, UserRoleModel


class MysqlRoleRepository:
    """MySQL 角色与操作权限仓储。"""

    # 作用：保存异步会话工厂。
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：创建角色并分配权限。
    async def create(self, name: str, permission_codes: tuple[str, ...]) -> Role:
        """创建角色。"""
        role_id = str(uuid4())
        async with self._session_factory() as session:
            session.add(RoleModel(role_id=role_id, name=name.strip(), status="active"))
            for code in permission_codes:
                session.add(RolePermissionModel(role_id=role_id, permission_code=code))
            await session.commit()
        return Role(role_id, name, "active", permission_codes)

    # 作用：按 ID 查询角色。
    async def get(self, role_id: str) -> Role | None:
        """读取角色。"""
        async with self._session_factory() as session:
            model = await session.get(RoleModel, role_id)
            if model is None:
                return None
            codes = tuple((await session.scalars(select(RolePermissionModel.permission_code).where(RolePermissionModel.role_id == role_id))).all())
            return Role(model.role_id, model.name, model.status, codes)

    # 作用：查询全部角色。
    async def list_all(self) -> tuple[Role, ...]:
        """返回角色列表。"""
        async with self._session_factory() as session:
            models = (await session.scalars(select(RoleModel).order_by(RoleModel.name))).all()
            result = []
            for model in models:
                codes = tuple((await session.scalars(select(RolePermissionModel.permission_code).where(RolePermissionModel.role_id == model.role_id))).all())
                result.append(Role(model.role_id, model.name, model.status, codes))
            return tuple(result)

    # 作用：更新角色状态。
    async def set_status(self, role_id: str, status: str) -> Role:
        """更新角色状态。"""
        async with self._session_factory() as session:
            model = await session.get(RoleModel, role_id)
            if model is None:
                raise NotFoundError("role not found")
            model.status = status
            user_ids = select(UserRoleModel.user_id).where(UserRoleModel.role_id == role_id)
            await session.execute(
                update(UserModel)
                .where(UserModel.user_id.in_(user_ids))
                .values(permission_version=UserModel.permission_version + 1)
            )
            await session.commit()
            codes = tuple((await session.scalars(select(RolePermissionModel.permission_code).where(RolePermissionModel.role_id == role_id))).all())
            return Role(model.role_id, model.name, model.status, codes)

    # 作用：替换角色操作权限。
    async def set_permissions(self, role_id: str, permission_codes: tuple[str, ...]) -> Role:
        """替换角色权限。"""
        async with self._session_factory() as session:
            model = await session.get(RoleModel, role_id)
            if model is None:
                raise NotFoundError("role not found")
            await session.execute(delete(RolePermissionModel).where(RolePermissionModel.role_id == role_id))
            for code in permission_codes:
                session.add(RolePermissionModel(role_id=role_id, permission_code=code))
            user_ids = select(UserRoleModel.user_id).where(UserRoleModel.role_id == role_id)
            await session.execute(
                update(UserModel)
                .where(UserModel.user_id.in_(user_ids))
                .values(permission_version=UserModel.permission_version + 1)
            )
            await session.commit()
            return Role(model.role_id, model.name, model.status, permission_codes)

    # 作用：删除未被用户引用的角色。
    async def delete(self, role_id: str) -> None:
        """删除角色及其权限关联。"""
        async with self._session_factory() as session:
            model = await session.get(RoleModel, role_id)
            if model is None:
                raise NotFoundError("role not found")
            reference = await session.scalar(
                select(UserRoleModel.user_id).where(UserRoleModel.role_id == role_id).limit(1)
            )
            if reference:
                raise ConflictError("role is still assigned to users")
            await session.execute(delete(RolePermissionModel).where(RolePermissionModel.role_id == role_id))
            await session.delete(model)
            await session.commit()

    # 作用：查询系统权限定义。
    async def list_permissions(self) -> tuple[PermissionDefinition, ...]:
        """返回操作权限定义。"""
        async with self._session_factory() as session:
            models = (await session.scalars(select(IamPermissionModel).order_by(IamPermissionModel.permission_code))).all()
        return tuple(PermissionDefinition(item.permission_code, item.name, item.permission_type, item.parent_code) for item in models)
