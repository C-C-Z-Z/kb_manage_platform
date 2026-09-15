"""提供知识分类字典应用服务。"""

from kb_manage_platform.domain.models import KnowledgeCategory
from kb_manage_platform.domain.ports import AuditPort, KnowledgeCategoryRepositoryPort


class CategoryService:
    """编排分类字典的增删改查用例。"""

    def __init__(self, repository: KnowledgeCategoryRepositoryPort, audit: AuditPort) -> None:
        self._repository = repository
        self._audit = audit

    async def list_all(self) -> tuple[KnowledgeCategory, ...]:
        """返回全部分类。"""
        return await self._repository.list_all()

    async def create(
        self,
        category_id: str,
        name: str,
        description: str,
        sort_order: int,
        operator_id: str,
    ) -> KnowledgeCategory:
        """创建分类并写入审计。"""
        normalized_id = category_id.strip()
        if not normalized_id or not name.strip():
            raise ValueError("category id and name must not be empty")
        category = await self._repository.create(
            normalized_id, name, description, sort_order
        )
        await self._audit.record(
            "category.created",
            {"user_id": operator_id, "category_id": category.category_id},
        )
        return category

    async def update(
        self,
        category_id: str,
        name: str,
        description: str,
        status: str,
        sort_order: int,
        operator_id: str,
    ) -> KnowledgeCategory:
        """更新分类并写入审计。"""
        if not name.strip():
            raise ValueError("category name must not be empty")
        category = await self._repository.update(
            category_id, name, description, status, sort_order
        )
        await self._audit.record(
            "category.updated",
            {"user_id": operator_id, "category_id": category.category_id},
        )
        return category

    async def delete(self, category_id: str, operator_id: str) -> None:
        """删除未被引用的分类并写入审计。"""
        await self._repository.delete(category_id)
        await self._audit.record(
            "category.deleted",
            {"user_id": operator_id, "category_id": category_id},
        )