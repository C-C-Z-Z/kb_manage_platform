"""使用 SQLAlchemy 执行四维候选知识鉴权。"""

from collections import defaultdict
from dataclasses import replace
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.domain.models import PermissionGrant, PermissionScope, RetrievedCandidate, UserContext
from kb_manage_platform.domain.services.permissions import PermissionPolicy, permission_signature
from kb_manage_platform.infrastructure.mysql.models import (
    KnowledgePermissionModel,
    KnowledgeUnitModel,
    KnowledgeVersionModel,
)


class MysqlAuthorizationEngine:
    """从 MySQL 批量加载知识权限并执行 OR 鉴权。"""

    # 作用：保存会话工厂和权限策略。
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        policy: PermissionPolicy,
    ) -> None:
        self._session_factory = session_factory
        self._policy = policy

    # 作用：批量过滤当前用户有权访问的候选知识。
    async def filter_allowed(
        self,
        user: UserContext,
        candidates: Sequence[RetrievedCandidate],
    ) -> Sequence[RetrievedCandidate]:
        """返回授权候选，默认拒绝无权限知识。"""
        if not candidates or not user.is_active:
            return []
        knowledge_ids = tuple({candidate.knowledge_id for candidate in candidates})
        version_ids = tuple({candidate.version_id for candidate in candidates})
        async with self._session_factory() as session:
            permission_rows = (
                await session.scalars(
                    select(KnowledgePermissionModel).where(
                        KnowledgePermissionModel.knowledge_id.in_(knowledge_ids)
                    )
                )
            ).all()
            units = (
                await session.scalars(
                    select(KnowledgeUnitModel).where(
                        KnowledgeUnitModel.knowledge_id.in_(knowledge_ids),
                        KnowledgeUnitModel.status == "published",
                    )
                )
            ).all()
            versions = (
                await session.scalars(
                    select(KnowledgeVersionModel).where(
                        KnowledgeVersionModel.version_id.in_(version_ids),
                        KnowledgeVersionModel.status == "indexed",
                    )
                )
            ).all()
        current_version_by_knowledge = {
            unit.knowledge_id: unit.current_version_id for unit in units
        }
        indexed_versions = {version.version_id for version in versions}
        grants_by_knowledge: dict[str, list[PermissionGrant]] = defaultdict(list)
        for row in permission_rows:
            grants_by_knowledge[row.knowledge_id].append(
                PermissionGrant(
                    scope=PermissionScope(row.scope),
                    subject_id=row.subject_id,
                    include_descendants=row.include_descendants,
                )
            )
        allowed: list[RetrievedCandidate] = []
        for candidate in candidates:
            if current_version_by_knowledge.get(candidate.knowledge_id) != candidate.version_id:
                continue
            if candidate.version_id not in indexed_versions:
                continue
            grants = grants_by_knowledge.get(candidate.knowledge_id, [])
            if not self._policy.matches(user, grants):
                continue
            allowed.append(
                replace(
                    candidate,
                    metadata={
                        **candidate.metadata,
                        "permission_signature": permission_signature(grants),
                    },
                )
            )
        return allowed
