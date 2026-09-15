"""提供部门树管理服务。"""

from kb_manage_platform.domain.models import Department
from kb_manage_platform.domain.ports import AuditPort, DepartmentRepositoryPort


class OrganizationService:
    """部门管理用例。"""

    # 作用：注入部门仓储和审计端口。
    def __init__(self, repository: DepartmentRepositoryPort, audit: AuditPort) -> None:
        self._repository = repository
        self._audit = audit

    # 作用：查询部门树数据。
    async def list_departments(self) -> tuple[Department, ...]:
        """返回部门列表。"""
        return await self._repository.list_all()

    # 作用：创建部门。
    async def create_department(
        self, name: str, parent_id: str, operator_id: str, sort_order: int = 0
    ) -> Department:
        """创建部门并记录审计。"""
        department = await self._repository.create(name, parent_id, operator_id, sort_order)
        await self._audit.record("iam.department.created", {"operator_id": operator_id, "department_id": department.department_id})
        return department

    # 作用：更新部门。
    async def update_department(
        self,
        department_id: str,
        name: str,
        parent_id: str,
        operator_id: str,
        sort_order: int = 0,
    ) -> Department:
        """更新部门并记录审计。"""
        department = await self._repository.update(department_id, name, parent_id, operator_id, sort_order)
        await self._audit.record("iam.department.updated", {"operator_id": operator_id, "department_id": department_id})
        return department

    # 作用：更新部门状态。
    async def set_department_status(self, department_id: str, status: str, operator_id: str) -> Department:
        """更新部门状态。"""
        department = await self._repository.set_status(department_id, status)
        await self._audit.record("iam.department.status_changed", {"operator_id": operator_id, "department_id": department_id, "status": status})
        return department

    # 作用：删除空部门。
    async def delete_department(self, department_id: str, operator_id: str) -> None:
        """删除部门并记录审计。"""
        await self._repository.delete(department_id)
        await self._audit.record("iam.department.deleted", {"operator_id": operator_id, "department_id": department_id})
