"""用户账号管理路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from kb_manage_platform.api.dependencies import AccountServiceDep, require_permission
from kb_manage_platform.api.schemas.iam import AssignRolesRequest, ResetPasswordRequest, StatusRequest, UserCreateRequest
from kb_manage_platform.domain.models import AccountStatus, UserAccount, UserContext

router = APIRouter(prefix="/users", tags=["accounts"])
RequireManage = Annotated[UserContext, Depends(require_permission("iam:user:manage"))]


# 作用：转换用户账号响应。
def user_response(item: UserAccount) -> dict[str, object]:
    """返回账号字段。"""
    return {"user_id": item.user_id, "username": item.username, "department_id": item.department_id, "status": item.status.value, "permission_version": item.permission_version, "role_ids": list(item.role_ids)}


# 作用：查询用户列表。
@router.get("")
async def list_users(_: RequireManage, service: AccountServiceDep):
    """返回用户列表。"""
    return {"items": [user_response(item) for item in await service.list_users()]}


# 作用：创建用户账号。
@router.post("")
async def create_user(payload: UserCreateRequest, user: RequireManage, service: AccountServiceDep):
    """创建用户。"""
    account = await service.create_user(payload.username, payload.password, payload.department_id, tuple(payload.role_ids), user.user_id)
    return user_response(account)


# 作用：更新账号状态。
@router.post("/{user_id}/status")
async def set_user_status(user_id: str, payload: StatusRequest, operator: RequireManage, service: AccountServiceDep):
    """更新用户状态。"""
    account = await service.set_user_status(user_id, AccountStatus(payload.status), operator.user_id)
    return user_response(account)


# 作用：分配用户角色。
@router.put("/{user_id}/roles")
async def assign_roles(user_id: str, payload: AssignRolesRequest, operator: RequireManage, service: AccountServiceDep):
    """更新用户角色。"""
    account = await service.assign_roles(user_id, tuple(payload.role_ids), operator.user_id)
    return user_response(account)


# 作用：管理员重置密码。
@router.post("/{user_id}/password-reset")
async def reset_password(user_id: str, payload: ResetPasswordRequest, operator: RequireManage, service: AccountServiceDep):
    """重置密码。"""
    await service.reset_password(user_id, payload.new_password, operator.user_id)
    return {"message": "password reset"}
