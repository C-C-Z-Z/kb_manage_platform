"""登录、退出和修改密码路由。"""

from fastapi import APIRouter

from kb_manage_platform.api.dependencies import AuthServiceDep, CurrentUserDep
from kb_manage_platform.api.schemas.iam import (
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)
from kb_manage_platform.domain.models import UserAccount, UserContext

router = APIRouter(prefix="/auth", tags=["auth"])


def _profile(account: UserAccount, user: UserContext) -> CurrentUserResponse:
    """构造当前用户响应。"""
    return CurrentUserResponse(
        user_id=user.user_id,
        username=account.username,
        department_id=user.department_id,
        role_ids=list(user.role_ids),
        status=account.status.value,
        permission_codes=list(user.permission_codes),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    """登录接口。"""
    token = await service.login(payload.username, payload.password)
    account, user = await service.get_profile(token.user_context.user_id)
    return TokenResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user=_profile(account, user),
    )


@router.get("/me", response_model=CurrentUserResponse)
async def current_user(user: CurrentUserDep, service: AuthServiceDep) -> CurrentUserResponse:
    """返回当前登录用户资料。"""
    account, context = await service.get_profile(user.user_id)
    return _profile(account, context)


@router.post("/logout")
async def logout(user: CurrentUserDep, service: AuthServiceDep) -> dict[str, int]:
    """退出接口。"""
    return {"permission_version": await service.logout(user.user_id)}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user: CurrentUserDep,
    service: AuthServiceDep,
) -> dict[str, str]:
    """修改密码接口。"""
    await service.change_password(user.user_id, payload.current_password, payload.new_password)
    return {"message": "password changed"}
