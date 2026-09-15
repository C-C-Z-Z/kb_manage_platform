"""实现知识四维权限的 MySQL 仓储。"""

from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.infrastructure.mysql.models import KnowledgePermissionModel
from kb_manage_platform.domain.models import KnowledgePermissionSet, PermissionGrant, PermissionScope


class MysqlKnowledgePermissionRepository:
    """基于 SQLAlchemy AsyncSession 的权限仓储。"""

    # 作用：保存异步会话工厂。
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：整体替换知识单元四维权限。
    async def replace_grants(
        self,
        knowledge_id: str,
        grants: tuple[PermissionGrant, ...],
        operator_id: str,
    ) -> KnowledgePermissionSet:
        """删除旧规则并写入新规则。"""
        async with self._session_factory() as session:
            current_version = await session.scalar(
                select(func.max(KnowledgePermissionModel.permission_version)).where(
                    KnowledgePermissionModel.knowledge_id == knowledge_id
                )
            )
            permission_version = (current_version or 0) + 1
            await session.execute(
                delete(KnowledgePermissionModel).where(
                    KnowledgePermissionModel.knowledge_id == knowledge_id
                )
            )
            for grant in grants:
                session.add(
                    KnowledgePermissionModel(
                        knowledge_id=knowledge_id,
                        scope=grant.scope.value,
                        subject_id=grant.subject_id,
                        include_descendants=grant.include_descendants,
                        permission_version=permission_version,
                        created_by=operator_id,
                        updated_by=operator_id,
                    )
                )
            await session.commit()
        return KnowledgePermissionSet(knowledge_id, grants, permission_version)

    # 作用：批量查询多个知识单元的权限规则。
    async def list_grants_batch(
        self, knowledge_ids: Sequence[str]
    ) -> dict[str, KnowledgePermissionSet]:
        """返回知识 ID 到权限集合的映射。"""
        if not knowledge_ids:
            return {}
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(KnowledgePermissionModel).where(
                        KnowledgePermissionModel.knowledge_id.in_(tuple(knowledge_ids))
                    )
                )
            ).all()
        grouped: dict[str, list[KnowledgePermissionModel]] = {}
        for row in rows:
            grouped.setdefault(row.knowledge_id, []).append(row)
        return {
            knowledge_id: KnowledgePermissionSet(
                knowledge_id=knowledge_id,
                grants=tuple(
                    PermissionGrant(
                        scope=PermissionScope(row.scope),
                        subject_id=row.subject_id,
                        include_descendants=row.include_descendants,
                    )
                    for row in grouped.get(knowledge_id, [])
                ),
                permission_version=max(
                    (row.permission_version for row in grouped.get(knowledge_id, [])),
                    default=0,
                ),
            )
            for knowledge_id in knowledge_ids
        }

    # 作用：查询知识单元四维权限。
    async def list_grants(self, knowledge_id: str) -> KnowledgePermissionSet:
        """读取 knowledge_permission 表。"""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(KnowledgePermissionModel).where(
                        KnowledgePermissionModel.knowledge_id == knowledge_id
                    )
                )
            ).all()
        if not rows:
            return KnowledgePermissionSet(knowledge_id=knowledge_id, grants=())
        grants = tuple(
            PermissionGrant(
                scope=PermissionScope(row.scope),
                subject_id=row.subject_id,
                include_descendants=row.include_descendants,
            )
            for row in rows
        )
        return KnowledgePermissionSet(
            knowledge_id=knowledge_id,
            grants=grants,
            permission_version=max(row.permission_version for row in rows),
        )

