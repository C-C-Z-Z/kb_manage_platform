"""使用 SQLAlchemy 管理知识缺口和补充草稿闭环。"""

import hashlib
import re
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.domain.models import KnowledgeGap, KnowledgeGapStatus, KnowledgeGapType
from kb_manage_platform.infrastructure.mysql.models import (
    KnowledgeGapModel,
    KnowledgeGapSourceModel,
    KnowledgeSupplementDraftModel,
)


class MysqlKnowledgeGapRepository:
    """知识缺口、来源和补充草稿仓储。"""

    # 作用：保存异步会话工厂。
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：批量保存或聚合知识缺口。
    async def upsert_gaps(self, gaps: tuple[KnowledgeGap, ...]) -> None:
        """按代表问题哈希聚合缺口。"""
        async with self._session_factory() as session:
            for gap in gaps:
                normalized_hash = self.question_hash(gap.representative_question)
                existing = await session.scalar(
                    select(KnowledgeGapModel).where(
                        KnowledgeGapModel.normalized_hash == normalized_hash
                    )
                )
                if existing is None:
                    session.add(
                        KnowledgeGapModel(
                            gap_id=gap.gap_id,
                            representative_question=gap.representative_question,
                            normalized_hash=normalized_hash,
                            gap_type=gap.gap_type.value,
                            status=gap.status.value,
                            frequency=gap.frequency,
                            department_ids=list(gap.department_ids),
                            max_similarity=gap.max_similarity,
                            suggested_category=gap.suggested_category,
                        )
                    )
                else:
                    existing.frequency += gap.frequency
                    existing.max_similarity = max(existing.max_similarity, gap.max_similarity)
                    existing.department_ids = sorted(
                        set(existing.department_ids or []) | set(gap.department_ids)
                    )
                for request_id in gap.source_request_ids:
                    session.add(
                        KnowledgeGapSourceModel(
                            gap_id=gap.gap_id,
                            request_id=request_id,
                        )
                    )
            await session.commit()

    # 作用：按 ID 查询知识缺口。
    async def get_gap(self, gap_id: str) -> KnowledgeGap | None:
        """读取单个知识缺口。"""
        async with self._session_factory() as session:
            row = await session.get(KnowledgeGapModel, gap_id)
            return self._to_gap(row) if row else None
    # 作用：按状态查询知识缺口。
    async def list_gaps(self, status: KnowledgeGapStatus | None = None) -> tuple[KnowledgeGap, ...]:
        """读取知识缺口列表。"""
        statement = select(KnowledgeGapModel)
        if status is not None:
            statement = statement.where(KnowledgeGapModel.status == status.value)
        async with self._session_factory() as session:
            rows = (await session.scalars(statement.order_by(KnowledgeGapModel.updated_at.desc()))).all()
        return tuple(self._to_gap(row) for row in rows)

    # 作用：创建补充草稿和知识单元关联。
    async def create_supplement_draft(
        self,
        gap_id: str,
        title: str,
        category_id: str,
        knowledge_id: str,
        operator_id: str,
    ) -> str:
        """写入草稿关联并将缺口标记为已转草稿。"""
        async with self._session_factory() as session:
            gap = await session.get(KnowledgeGapModel, gap_id)
            if gap is None:
                raise LookupError(f"knowledge gap not found: {gap_id}")
            draft_id = str(uuid4())
            session.add(
                KnowledgeSupplementDraftModel(
                    draft_id=draft_id,
                    gap_id=gap_id,
                    title=title,
                    category_id=category_id or gap.suggested_category,
                    knowledge_id=knowledge_id,
                    status="draft",
                    created_by=operator_id,
                )
            )
            gap.status = KnowledgeGapStatus.CONVERTED.value
            await session.commit()
            return draft_id

    # 作用：知识发布后自动解决所有关联缺口。
    async def resolve_by_knowledge(self, knowledge_id: str) -> int:
        """返回解决的缺口数量。"""
        async with self._session_factory() as session:
            drafts = (
                await session.scalars(
                    select(KnowledgeSupplementDraftModel).where(
                        KnowledgeSupplementDraftModel.knowledge_id == knowledge_id
                    )
                )
            ).all()
            count = 0
            for draft in drafts:
                gap = await session.get(KnowledgeGapModel, draft.gap_id)
                if gap is not None and gap.status != KnowledgeGapStatus.RESOLVED.value:
                    gap.status = KnowledgeGapStatus.RESOLVED.value
                    draft.status = "published"
                    count += 1
            await session.commit()
            return count

    # 作用：更新知识缺口状态和原因。
    async def set_status(self, gap_id: str, status: KnowledgeGapStatus, reason: str = "") -> None:
        """更新知识缺口状态。"""
        async with self._session_factory() as session:
            gap = await session.get(KnowledgeGapModel, gap_id)
            if gap is None:
                raise LookupError(f"knowledge gap not found: {gap_id}")
            gap.status = status.value
            if reason:
                gap.reason = reason
            await session.commit()

    # 作用：标准化问题并计算 SHA-256 哈希。
    @staticmethod
    def question_hash(question: str) -> str:
        """返回问题哈希。"""
        normalized = re.sub(r"\s+", " ", question.strip().casefold())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    # 作用：将 ORM 缺口转换为领域模型。
    @staticmethod
    def _to_gap(row: KnowledgeGapModel) -> KnowledgeGap:
        """转换知识缺口模型。"""
        return KnowledgeGap(
            gap_id=row.gap_id,
            representative_question=row.representative_question,
            gap_type=KnowledgeGapType(row.gap_type),
            status=KnowledgeGapStatus(row.status),
            frequency=row.frequency,
            department_ids=tuple(row.department_ids or []),
            max_similarity=row.max_similarity,
            suggested_category=row.suggested_category,
        )