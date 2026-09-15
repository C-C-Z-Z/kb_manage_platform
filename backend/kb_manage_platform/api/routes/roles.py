"""角色和操作权限管理路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from kb_manage_platform.api.dependencies import RoleServiceDep, require_permission
from kb_manage_platform.api.schemas.iam import RoleCreateRequest, SetPermissionsRequest, StatusRequest
from kb_manage_platform.domain.models import Role, UserContext

router = APIRouter(prefix="/roles", tags=["roles"])
RequireManage = Annotated[UserContext, Depends(require_permission("iam:role:manage"))]


# 作用：转换角色响应。
def role_response(item: Role) -> dict[str, object]:
    """返回角色字段。"""
    return {"role_id": item.role_id, "name": item.name, "status": item.status, "permission_codes": list(item.permission_codes)}


# 作用：查询角色列表。
@router.get("")
async def list_roles(_: RequireManage, service: RoleServiceDep):
    """返回角色列表。"""
    return {"items": [role_response(item) for item in await service.list_roles()]}


# 作用：查询操作权限定义。
@router.get("/permissions")
async def list_permissions(_: RequireManage, service: RoleServiceDep):
    """返回权限定义。"""
    return {"items": [{"permission_code": item.permission_code, "name": item.name, "permission_type": item.permission_type, "parent_code": item.parent_code} for item in await service.list_permissions()]}


# 作用：创建角色。
@router.post("")
async def create_role(payload: RoleCreateRequest, user: RequireManage, service: RoleServiceDep):
    """创建角色。"""
    return role_response(await service.create_role(payload.name, tuple(payload.permission_codes), user.user_id))


# 作用：更新角色状态。
@router.post("/{role_id}/status")
async def set_role_status(role_id: str, payload: StatusRequest, user: RequireManage, service: RoleServiceDep):
    """更新角色状态。"""
    return role_response(await service.set_role_status(role_id, payload.status, user.user_id))


# 作用：替换角色权限。
@router.put("/{role_id}/permissions")
async def set_role_permissions(role_id: str, payload: SetPermissionsRequest, user: RequireManage, service: RoleServiceDep):
    """更新角色权限。"""
    return role_response(await service.set_permissions(role_id, tuple(payload.permission_codes), user.user_id))


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: str,
    user: RequireManage,
    service: RoleServiceDep,
) -> None:
    """删除未被用户引用的角色。"""
    await service.delete_role(role_id, user.user_id)
