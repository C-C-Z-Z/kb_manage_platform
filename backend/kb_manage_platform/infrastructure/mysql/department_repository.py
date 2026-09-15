"""使用 SQLAlchemy 管理部门树。"""

from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.common.errors import ConflictError, NotFoundError
from kb_manage_platform.domain.models import Department
from kb_manage_platform.infrastructure.mysql.models import DepartmentModel, UserModel


class MysqlDepartmentRepository:
    """MySQL 部门仓储。"""

    # 作用：保存异步会话工厂。
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：创建部门并维护路径。
    async def create(
        self, name: str, parent_id: str, operator_id: str, sort_order: int = 0
    ) -> Department:
        """创建部门。"""
        async with self._session_factory() as session:
            parent_path = ""
            if parent_id:
                parent = await session.get(DepartmentModel, parent_id)
                if parent is None:
                    raise NotFoundError("parent department not found")
                parent_path = parent.path
            department_id = str(uuid4())
            path = f"{parent_path}/{department_id}".strip("/")
            model = DepartmentModel(
                department_id=department_id,
                name=name.strip(),
                parent_id=parent_id or None,
                path=path,
                status="active",
                sort_order=sort_order,
            )
            session.add(model)
            await session.commit()
            return self._to_domain(model)

    # 作用：更新部门名称或父部门。
    async def update(
        self,
        department_id: str,
        name: str,
        parent_id: str,
        operator_id: str,
        sort_order: int = 0,
    ) -> Department:
        """更新部门。"""
        async with self._session_factory() as session:
            model = await session.get(DepartmentModel, department_id)
            if model is None:
                raise NotFoundError("department not found")
            if parent_id != (model.parent_id or ""):
                has_children = await session.scalar(
                    select(DepartmentModel.department_id).where(DepartmentModel.parent_id == department_id).limit(1)
                )
                if has_children:
                    raise ConflictError("cannot move department with children")
                parent_path = ""
                if parent_id:
                    parent = await session.get(DepartmentModel, parent_id)
                    if parent is None:
                        raise NotFoundError("parent department not found")
                    parent_path = parent.path
                model.parent_id = parent_id or None
                model.path = f"{parent_path}/{department_id}".strip("/")
            model.name = name.strip() or model.name
            model.sort_order = sort_order
            await session.execute(
                update(UserModel)
                .where(UserModel.department_id == department_id)
                .values(permission_version=UserModel.permission_version + 1)
            )
            await session.commit()
            return self._to_domain(model)

    # 作用：按 ID 查询部门。
    async def get(self, department_id: str) -> Department | None:
        """读取部门。"""
        async with self._session_factory() as session:
            model = await session.get(DepartmentModel, department_id)
            return self._to_domain(model) if model else None

    # 作用：查询全部部门。
    async def list_all(self) -> tuple[Department, ...]:
        """返回部门列表。"""
        async with self._session_factory() as session:
            models = (await session.scalars(select(DepartmentModel).order_by(DepartmentModel.sort_order, DepartmentModel.path))).all()
        return tuple(self._to_domain(model) for model in models)

    # 作用：更新部门状态。
    async def set_status(self, department_id: str, status: str) -> Department:
        """更新部门状态。"""
        async with self._session_factory() as session:
            model = await session.get(DepartmentModel, department_id)
            if model is None:
                raise NotFoundError("department not found")
            model.status = status
            await session.execute(
                update(UserModel)
                .where(UserModel.department_id == department_id)
                .values(permission_version=UserModel.permission_version + 1)
            )
            await session.commit()
            return self._to_domain(model)

    # 作用：删除无子部门和成员的部门。
    async def delete(self, department_id: str) -> None:
        """删除空部门。"""
        async with self._session_factory() as session:
            child = await session.scalar(select(DepartmentModel.department_id).where(DepartmentModel.parent_id == department_id).limit(1))
            user = await session.scalar(select(UserModel.user_id).where(UserModel.department_id == department_id).limit(1))
            if child or user:
                raise ConflictError("department is not empty")
            model = await session.get(DepartmentModel, department_id)
            if model is None:
                raise NotFoundError("department not found")
            await session.delete(model)
            await session.commit()

    # 作用：转换部门领域模型。
    @staticmethod
    def _to_domain(model: DepartmentModel) -> Department:
        """转换部门模型。"""
        return Department(model.department_id, model.name, model.parent_id or "", model.path, model.status)
