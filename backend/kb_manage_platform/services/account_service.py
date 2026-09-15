"""提供用户账号管理服务。"""

from kb_manage_platform.domain.models import AccountStatus, UserAccount
from kb_manage_platform.domain.ports import AccountRepositoryPort, AuditPort, PasswordHasherPort


class AccountService:
    """用户账号管理用例。"""

    # 作用：注入账号仓储、密码哈希和审计端口。
    def __init__(self, repository: AccountRepositoryPort, password_hasher: PasswordHasherPort, audit: AuditPort) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._audit = audit

    # 作用：查询用户列表。
    async def list_users(self) -> tuple[UserAccount, ...]:
        """返回账号列表。"""
        return await self._repository.list_all()

    # 作用：按用户 ID 查询账号。
    async def get_user(self, user_id: str) -> UserAccount | None:
        """返回账号详情。"""
        return await self._repository.get(user_id)

    # 作用：创建用户账号。
    async def create_user(self, username: str, password: str, department_id: str, role_ids: tuple[str, ...], operator_id: str) -> UserAccount:
        """创建账号并记录审计。"""
        password_hash = self._password_hasher.hash(password)
        account = await self._repository.create(username, password_hash, department_id, role_ids)
        await self._audit.record("iam.user.created", {"operator_id": operator_id, "user_id": account.user_id})
        return account

    # 作用：更新账号状态并强制令牌失效。
    async def set_user_status(self, user_id: str, status: AccountStatus, operator_id: str) -> UserAccount:
        """更新账号状态。"""
        account = await self._repository.set_status(user_id, status)
        await self._audit.record("iam.user.status_changed", {"operator_id": operator_id, "user_id": user_id, "status": status.value})
        return account

    # 作用：替换用户角色。
    async def assign_roles(self, user_id: str, role_ids: tuple[str, ...], operator_id: str) -> UserAccount:
        """更新用户角色。"""
        account = await self._repository.assign_roles(user_id, role_ids)
        await self._audit.record("iam.user.roles_changed", {"operator_id": operator_id, "user_id": user_id, "role_ids": list(role_ids)})
        return account

    # 作用：管理员重置用户密码。
    async def reset_password(self, user_id: str, new_password: str, operator_id: str) -> None:
        """重置密码并强制令牌失效。"""
        await self._repository.update_password_hash(user_id, self._password_hasher.hash(new_password))
        await self._audit.record("iam.user.password_reset", {"operator_id": operator_id, "user_id": user_id})
