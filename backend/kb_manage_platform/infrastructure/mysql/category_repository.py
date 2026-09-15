"""实现知识分类字典的 MySQL 仓储。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.domain.models import KnowledgeCategory
from kb_manage_platform.infrastructure.mysql.models import (
    KnowledgeCategoryModel,
    KnowledgeUnitModel,
)


class MysqlKnowledgeCategoryRepository:
    """基于 SQLAlchemy 的知识分类仓储。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_all(self) -> tuple[KnowledgeCategory, ...]:
        """返回按排序字段排列的分类列表。"""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(KnowledgeCategoryModel).order_by(
                        KnowledgeCategoryModel.sort_order.asc(),
                        KnowledgeCategoryModel.created_at.asc(),
                    )
                )
            ).all()
        return tuple(self._to_domain(row) for row in rows)

    async def create(
        self, category_id: str, name: str, description: str, sort_order: int
    ) -> KnowledgeCategory:
        """创建分类。"""
        async with self._session_factory() as session:
            model = KnowledgeCategoryModel(
                category_id=category_id.strip(),
                name=name.strip(),
                description=description.strip(),
                status="active",
                sort_order=sort_order,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._to_domain(model)

    async def update(
        self,
        category_id: str,
        name: str,
        description: str,
        status: str,
        sort_order: int,
    ) -> KnowledgeCategory:
        """更新分类。"""
        if status not in {"active", "disabled"}:
            raise ValueError("category status must be active or disabled")
        async with self._session_factory() as session:
            model = await session.get(KnowledgeCategoryModel, category_id)
            if model is None:
                raise LookupError(f"category not found: {category_id}")
            model.name = name.strip()
            model.description = description.strip()
            model.status = status
            model.sort_order = sort_order
            await session.commit()
            await session.refresh(model)
            return self._to_domain(model)

    async def delete(self, category_id: str) -> None:
        """删除未被知识引用的分类。"""
        async with self._session_factory() as session:
            model = await session.get(KnowledgeCategoryModel, category_id)
            if model is None:
                raise LookupError(f"category not found: {category_id}")
            reference_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(KnowledgeUnitModel)
                    .where(KnowledgeUnitModel.category_id == category_id)
                )
                or 0
            )
            if reference_count:
                raise ValueError("category is still referenced by knowledge units")
            await session.delete(model)
            await session.commit()

    @staticmethod
    def _to_domain(model: KnowledgeCategoryModel) -> KnowledgeCategory:
        """转换 ORM 分类模型。"""
        return KnowledgeCategory(
            category_id=model.category_id,
            name=model.name,
            description=model.description,
            status=model.status,
            sort_order=model.sort_order,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )