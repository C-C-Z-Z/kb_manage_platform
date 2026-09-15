"""提供角色和操作权限管理服务。"""

from kb_manage_platform.domain.models import PermissionDefinition, Role
from kb_manage_platform.domain.ports import AuditPort, RoleRepositoryPort


class RoleService:
    """角色授权用例。"""

    # 作用：注入角色仓储和审计端口。
    def __init__(self, repository: RoleRepositoryPort, audit: AuditPort) -> None:
        self._repository = repository
        self._audit = audit

    # 作用：查询角色列表。
    async def list_roles(self) -> tuple[Role, ...]:
        """返回角色列表。"""
        return await self._repository.list_all()

    # 作用：创建角色。
    async def create_role(self, name: str, permission_codes: tuple[str, ...], operator_id: str) -> Role:
        """创建角色并记录审计。"""
        role = await self._repository.create(name, permission_codes)
        await self._audit.record("iam.role.created", {"operator_id": operator_id, "role_id": role.role_id})
        return role

    # 作用：删除未被用户引用的角色。
    async def delete_role(self, role_id: str, operator_id: str) -> None:
        """删除角色并记录审计。"""
        await self._repository.delete(role_id)
        await self._audit.record("iam.role.deleted", {"operator_id": operator_id, "role_id": role_id})

    # 作用：更新角色状态。
    async def set_role_status(self, role_id: str, status: str, operator_id: str) -> Role:
        """更新角色状态。"""
        role = await self._repository.set_status(role_id, status)
        await self._audit.record("iam.role.status_changed", {"operator_id": operator_id, "role_id": role_id, "status": status})
        return role

    # 作用：替换角色权限。
    async def set_permissions(self, role_id: str, permission_codes: tuple[str, ...], operator_id: str) -> Role:
        """更新角色权限。"""
        role = await self._repository.set_permissions(role_id, permission_codes)
        await self._audit.record("iam.role.permissions_changed", {"operator_id": operator_id, "role_id": role_id, "permission_codes": list(permission_codes)})
        return role

    # 作用：查询可选操作权限。
    async def list_permissions(self) -> tuple[PermissionDefinition, ...]:
        """返回权限定义。"""
        return await self._repository.list_permissions()
