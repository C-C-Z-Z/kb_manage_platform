"""提供登录、令牌校验、退出和密码修改服务。"""

import time
from datetime import UTC, datetime

from kb_manage_platform.common.errors import AuthenticationError, AuthorizationError
from kb_manage_platform.domain.models import AccountStatus, AuthToken, UserAccount, UserContext
from kb_manage_platform.domain.ports import (
    AccountRepositoryPort,
    AuditPort,
    IdentityRepositoryPort,
    PasswordHasherPort,
    TokenPort,
)


class AuthService:
    """本地账号认证与 JWT 会话服务。"""

    # 作用：保存认证所需端口和锁定策略。
    def __init__(
        self,
        account_repository: AccountRepositoryPort,
        identity_repository: IdentityRepositoryPort,
        password_hasher: PasswordHasherPort,
        token_service: TokenPort,
        audit: AuditPort,
        lock_threshold: int,
        lock_seconds: int,
    ) -> None:
        self._account_repository = account_repository
        self._identity_repository = identity_repository
        self._password_hasher = password_hasher
        self._token_service = token_service
        self._audit = audit
        self._lock_threshold = lock_threshold
        self._lock_seconds = lock_seconds

    # 作用：校验账号密码并签发 JWT。
    async def login(self, username: str, password: str) -> AuthToken:
        """返回登录令牌和用户上下文。"""
        record = await self._account_repository.get_by_username(username)
        if record is None:
            raise AuthenticationError("invalid username or password")
        account, password_hash = record
        now = int(time.time())
        if account.status is AccountStatus.DISABLED:
            raise AuthorizationError("account disabled")
        if account.locked_until_epoch > now:
            raise AuthenticationError("account temporarily locked")
        if not self._password_hasher.verify(password, password_hash):
            attempts = account.failed_login_attempts + 1
            locked_until = (
                datetime.fromtimestamp(now + self._lock_seconds, UTC)
                if attempts >= self._lock_threshold
                else None
            )
            await self._account_repository.record_login_failure(account.user_id, attempts, locked_until)
            raise AuthenticationError("invalid username or password")
        await self._account_repository.clear_login_failures(account.user_id)
        user = await self._identity_repository.get_user_context(account.user_id)
        token, expires_in = self._token_service.issue(user.user_id, user.permission_version)
        await self._audit.record(
            "auth.login",
            {"user_id": user.user_id, "username": account.username},
        )
        return AuthToken(token, "Bearer", expires_in, user)

    # 作用：验证 JWT 并加载最新用户权限上下文。
    async def authenticate(self, token: str) -> UserContext:
        """返回有效用户上下文。"""
        user_id, token_version = self._token_service.parse(token)
        user = await self._identity_repository.get_user_context(user_id)
        if not user.is_active or user.permission_version != token_version:
            raise AuthenticationError("session invalidated")
        return user

    # 作用：读取当前账号和权限上下文。
    async def get_profile(self, user_id: str) -> tuple[UserAccount, UserContext]:
        """返回账号资料和可信权限上下文。"""
        account = await self._account_repository.get(user_id)
        if account is None:
            raise AuthenticationError("account not found")
        user = await self._identity_repository.get_user_context(user_id)
        return account, user

    # 作用：退出发起者令牌并使当前令牌失效。
    async def logout(self, user_id: str) -> int:
        """返回新的权限版本。"""
        version = await self._account_repository.bump_permission_version(user_id)
        await self._audit.record("auth.logout", {"user_id": user_id})
        return version

    # 作用：校验旧密码并修改新密码，同时使已有令牌失效。
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        """修改用户密码。"""
        password_hash = await self._account_repository.get_password_hash(user_id)
        if not self._password_hasher.verify(current_password, password_hash):
            raise AuthenticationError("current password is incorrect")
        new_hash = self._password_hasher.hash(new_password)
        await self._account_repository.update_password_hash(user_id, new_hash)
        await self._audit.record("auth.password_changed", {"user_id": user_id})

