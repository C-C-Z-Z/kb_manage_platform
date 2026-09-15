"""部门管理路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from kb_manage_platform.api.dependencies import OrganizationServiceDep, require_permission
from kb_manage_platform.api.schemas.iam import DepartmentCreateRequest, DepartmentUpdateRequest, StatusRequest
from kb_manage_platform.domain.models import Department, UserContext

router = APIRouter(prefix="/departments", tags=["organization"])
RequireManage = Annotated[UserContext, Depends(require_permission("iam:department:manage"))]


# 作用：转换部门响应。
def department_response(item: Department) -> dict[str, str]:
    """返回部门字段。"""
    return {"department_id": item.department_id, "name": item.name, "parent_id": item.parent_id, "path": item.path, "status": item.status, "sort_order": item.sort_order}


# 作用：查询部门树数据。
@router.get("")
async def list_departments(_: RequireManage, service: OrganizationServiceDep):
    """返回部门列表。"""
    return {"items": [department_response(item) for item in await service.list_departments()]}


# 作用：创建部门。
@router.post("")
async def create_department(payload: DepartmentCreateRequest, user: RequireManage, service: OrganizationServiceDep):
    """创建部门。"""
    return department_response(await service.create_department(payload.name, payload.parent_id, user.user_id, payload.sort_order))


# 作用：更新部门。
@router.patch("/{department_id}")
async def update_department(department_id: str, payload: DepartmentUpdateRequest, user: RequireManage, service: OrganizationServiceDep):
    """更新部门。"""
    return department_response(await service.update_department(department_id, payload.name, payload.parent_id, user.user_id, payload.sort_order))


# 作用：更新部门状态。
@router.post("/{department_id}/status")
async def set_department_status(department_id: str, payload: StatusRequest, user: RequireManage, service: OrganizationServiceDep):
    """更新部门状态。"""
    return department_response(await service.set_department_status(department_id, payload.status, user.user_id))


# 作用：删除空部门。
@router.delete("/{department_id}")
async def delete_department(department_id: str, user: RequireManage, service: OrganizationServiceDep):
    """删除部门。"""
    await service.delete_department(department_id, user.user_id)
    return {"message": "deleted"}
