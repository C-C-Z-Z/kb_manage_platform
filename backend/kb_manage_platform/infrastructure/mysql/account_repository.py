"""使用 SQLAlchemy 管理用户账号、角色和登录状态。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.common.errors import NotFoundError
from kb_manage_platform.domain.models import AccountStatus, UserAccount
from kb_manage_platform.infrastructure.mysql.models import UserModel, UserRoleModel


class MysqlAccountRepository:
    """MySQL 用户账号仓储。"""

    # 作用：保存异步会话工厂。
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：创建本地账号并分配角色。
    async def create(self, username: str, password_hash: str, department_id: str, role_ids: tuple[str, ...]) -> UserAccount:
        """创建账号。"""
        user_id = str(uuid4())
        async with self._session_factory() as session:
            session.add(
                UserModel(
                    user_id=user_id,
                    username=username.strip(),
                    password_hash=password_hash,
                    department_id=department_id,
                    status=AccountStatus.ACTIVE.value,
                    permission_version=1,
                )
            )
            for role_id in role_ids:
                session.add(UserRoleModel(user_id=user_id, role_id=role_id))
            await session.commit()
        return UserAccount(user_id, username, department_id, AccountStatus.ACTIVE, 1, role_ids)

    # 作用：按用户名查询账号及密码哈希。
    async def get_by_username(self, username: str) -> tuple[UserAccount, str] | None:
        """按用户名读取账号。"""
        async with self._session_factory() as session:
            model = await session.scalar(select(UserModel).where(UserModel.username == username))
            if model is None:
                return None
            return await self._to_account(session, model), model.password_hash

    # 作用：按用户 ID 查询账号。
    async def get(self, user_id: str) -> UserAccount | None:
        """按 ID 读取账号。"""
        async with self._session_factory() as session:
            model = await session.get(UserModel, user_id)
            return await self._to_account(session, model) if model else None

    # 作用：查询全部账号。
    async def list_all(self) -> tuple[UserAccount, ...]:
        """返回账号列表。"""
        async with self._session_factory() as session:
            models = (await session.scalars(select(UserModel).order_by(UserModel.username))).all()
            return tuple([await self._to_account(session, model) for model in models])

    # 作用：更新账号状态并失效已有令牌。
    async def set_status(self, user_id: str, status: AccountStatus) -> UserAccount:
        """更新账号状态。"""
        async with self._session_factory() as session:
            model = await session.get(UserModel, user_id)
            if model is None:
                raise NotFoundError("user not found")
            model.status = status.value
            model.permission_version += 1
            await session.commit()
            return await self._to_account(session, model)

    # 作用：替换用户角色并失效已有令牌。
    async def assign_roles(self, user_id: str, role_ids: tuple[str, ...]) -> UserAccount:
        """替换用户角色。"""
        async with self._session_factory() as session:
            model = await session.get(UserModel, user_id)
            if model is None:
                raise NotFoundError("user not found")
            await session.execute(delete(UserRoleModel).where(UserRoleModel.user_id == user_id))
            for role_id in role_ids:
                session.add(UserRoleModel(user_id=user_id, role_id=role_id))
            model.permission_version += 1
            await session.commit()
            return await self._to_account(session, model)

    # 作用：按用户 ID 获取密码哈希。
    async def get_password_hash(self, user_id: str) -> str:
        """读取密码哈希。"""
        async with self._session_factory() as session:
            model = await session.get(UserModel, user_id)
            if model is None:
                raise NotFoundError("user not found")
            return model.password_hash

    # 作用：更新密码哈希并清除失败状态。
    async def update_password_hash(self, user_id: str, password_hash: str) -> None:
        """重置用户密码。"""
        async with self._session_factory() as session:
            model = await session.get(UserModel, user_id)
            if model is None:
                raise NotFoundError("user not found")
            model.password_hash = password_hash
            model.failed_login_attempts = 0
            model.locked_until = None
            model.permission_version += 1
            await session.commit()

    # 作用：记录登录失败次数和锁定时间。
    async def record_login_failure(self, user_id: str, failed_attempts: int, locked_until) -> None:
        """更新登录失败状态。"""
        async with self._session_factory() as session:
            await session.execute(
                update(UserModel)
                .where(UserModel.user_id == user_id)
                .values(failed_login_attempts=failed_attempts, locked_until=locked_until)
            )
            await session.commit()

    # 作用：清除登录失败记录并记录最后登录时间。
    async def clear_login_failures(self, user_id: str) -> None:
        """更新登录成功状态。"""
        async with self._session_factory() as session:
            model = await session.get(UserModel, user_id)
            if model is None:
                raise NotFoundError("user not found")
            model.failed_login_attempts = 0
            model.locked_until = None
            model.last_login_at = datetime.now(UTC)
            await session.commit()

    # 作用：递增用户权限版本。
    async def bump_permission_version(self, user_id: str) -> int:
        """返回新的权限版本。"""
        async with self._session_factory() as session:
            model = await session.get(UserModel, user_id)
            if model is None:
                raise NotFoundError("user not found")
            model.permission_version += 1
            await session.commit()
            return model.permission_version

    # 作用：读取账号角色。
    async def _to_account(self, session: AsyncSession, model: UserModel) -> UserAccount:
        """转换账号模型。"""
        role_ids = tuple((await session.scalars(select(UserRoleModel.role_id).where(UserRoleModel.user_id == model.user_id))).all())
        return UserAccount(
            user_id=model.user_id,
            username=model.username,
            department_id=model.department_id,
            status=AccountStatus(model.status),
            permission_version=model.permission_version,
            role_ids=role_ids,
            failed_login_attempts=model.failed_login_attempts,
            locked_until_epoch=int(model.locked_until.timestamp()) if model.locked_until else 0,
        )
