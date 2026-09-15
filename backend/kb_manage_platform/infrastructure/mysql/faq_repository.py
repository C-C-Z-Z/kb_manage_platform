"""使用 SQLAlchemy 管理 FAQ 查询、候选、审核、发布和权限。"""

import hashlib
import re
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.domain.models import (
    AnswerResult,
    Faq,
    FaqCandidate,
    FaqCandidateStatus,
    PermissionGrant,
    PermissionScope,
    UserContext,
)
from kb_manage_platform.domain.services.permissions import PermissionPolicy
from kb_manage_platform.infrastructure.mysql.models import (
    FaqCandidateModel,
    FaqCandidateSourceModel,
    FaqModel,
    FaqPermissionModel,
)


class MysqlFaqRepository:
    """FAQ 事实、候选和权限仓储。"""

    # 作用：保存会话工厂和权限策略。
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        policy: PermissionPolicy,
    ) -> None:
        self._session_factory = session_factory
        self._policy = policy

    # 作用：按规范化问题查询已发布 FAQ 并校验权限。
    async def lookup(self, question: str, user: UserContext) -> AnswerResult | None:
        """返回有权限访问的 FAQ 标准答案。"""
        normalized_hash = self.question_hash(question)
        async with self._session_factory() as session:
            faq = await session.scalar(
                select(FaqModel).where(
                    FaqModel.normalized_hash == normalized_hash,
                    FaqModel.status == "published",
                )
            )
            if faq is None:
                return None
            rows = (
                await session.scalars(
                    select(FaqPermissionModel).where(FaqPermissionModel.faq_id == faq.faq_id)
                )
            ).all()
        grants = tuple(self._to_grant(row.scope, row.subject_id, row.include_descendants) for row in rows)
        if not self._policy.matches(user, grants):
            return None
        return AnswerResult(answer=faq.answer_text)

    # 作用：保存或更新 FAQ，新 FAQ 默认保持草稿状态。
    async def save(self, question: str, answer: AnswerResult) -> None:
        """写入 FAQ 表。"""
        normalized_hash = self.question_hash(question)
        async with self._session_factory() as session:
            faq = await session.scalar(
                select(FaqModel).where(FaqModel.normalized_hash == normalized_hash)
            )
            if faq is None:
                session.add(
                    FaqModel(
                        faq_id=str(uuid4()),
                        standard_question=question.strip(),
                        normalized_hash=normalized_hash,
                        answer_text=answer.answer,
                        status="draft",
                    )
                )
            else:
                faq.answer_text = answer.answer
            await session.commit()

    # 作用：批量保存 FAQ 聚类候选和来源问答。
    async def save_candidates(self, candidates: tuple[FaqCandidate, ...]) -> None:
        """写入 knowledge_faq_candidate 和来源关联。"""
        async with self._session_factory() as session:
            for candidate in candidates:
                normalized_hash = self.question_hash(candidate.representative_question)
                existing = await session.scalar(
                    select(FaqCandidateModel).where(
                        FaqCandidateModel.normalized_hash == normalized_hash
                    )
                )
                if existing is None:
                    session.add(
                        FaqCandidateModel(
                            candidate_id=candidate.candidate_id,
                            representative_question=candidate.representative_question,
                            normalized_hash=normalized_hash,
                            standard_answer=candidate.standard_answer,
                            frequency=candidate.frequency,
                            distinct_users=candidate.distinct_users,
                            permission_signature=candidate.permission_signature,
                            status=candidate.status.value,
                            confidence=candidate.confidence,
                        )
                    )
                else:
                    existing.frequency = max(existing.frequency, candidate.frequency)
                    existing.distinct_users = max(existing.distinct_users, candidate.distinct_users)
                    existing.standard_answer = candidate.standard_answer
                    existing.permission_signature = candidate.permission_signature
                    existing.confidence = max(existing.confidence, candidate.confidence)
                for request_id in candidate.source_request_ids:
                    session.add(
                        FaqCandidateSourceModel(
                            candidate_id=candidate.candidate_id,
                            request_id=request_id,
                        )
                    )
            await session.commit()

    # 作用：按 ID 查询 FAQ 候选。
    async def get_candidate(self, candidate_id: str) -> FaqCandidate | None:
        """读取单个候选。"""
        async with self._session_factory() as session:
            row = await session.get(FaqCandidateModel, candidate_id)
            return self._to_candidate(row) if row else None
    # 作用：按状态查询 FAQ 候选。
    async def list_candidates(self, status: FaqCandidateStatus | None = None) -> tuple[FaqCandidate, ...]:
        """读取候选列表。"""
        statement = select(FaqCandidateModel)
        if status is not None:
            statement = statement.where(FaqCandidateModel.status == status.value)
        async with self._session_factory() as session:
            rows = (await session.scalars(statement.order_by(FaqCandidateModel.updated_at.desc()))).all()
        return tuple(self._to_candidate(row) for row in rows)

    # 作用：发布候选 FAQ 并写入独立权限。
    async def publish_candidate(
        self,
        candidate_id: str,
        grants: tuple[PermissionGrant, ...],
        operator_id: str,
    ) -> str:
        """发布 FAQ 并返回 FAQ ID。"""
        normalized_grants = self._policy.normalize(grants)
        async with self._session_factory() as session:
            candidate = await session.get(FaqCandidateModel, candidate_id)
            if candidate is None:
                raise LookupError(f"faq candidate not found: {candidate_id}")
            faq = await session.scalar(
                select(FaqModel).where(FaqModel.normalized_hash == candidate.normalized_hash)
            )
            if faq is None:
                faq = FaqModel(
                    faq_id=str(uuid4()),
                    standard_question=candidate.representative_question,
                    normalized_hash=candidate.normalized_hash,
                    answer_text=candidate.standard_answer,
                    status="published",
                )
                session.add(faq)
            else:
                faq.answer_text = candidate.standard_answer
                faq.status = "published"
            await session.execute(delete(FaqPermissionModel).where(FaqPermissionModel.faq_id == faq.faq_id))
            for grant in normalized_grants:
                session.add(
                    FaqPermissionModel(
                        faq_id=faq.faq_id,
                        scope=grant.scope.value,
                        subject_id=grant.subject_id,
                        include_descendants=grant.include_descendants,
                    )
                )
            candidate.status = FaqCandidateStatus.PUBLISHED.value
            candidate.reviewed_by = operator_id
            await session.commit()
            return faq.faq_id

    # 作用：查询已发布和已停用的 FAQ。
    async def list_published(self) -> tuple[Faq, ...]:
        """返回 FAQ 管理列表。"""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(FaqModel)
                    .where(FaqModel.status.in_(("published", "disabled")))
                    .order_by(FaqModel.updated_at.desc())
                )
            ).all()
        return tuple(self._to_faq(row) for row in rows)

    # 作用：更新已发布 FAQ 的问题和答案。
    async def update_published(
        self, faq_id: str, question: str, answer: str, operator_id: str
    ) -> Faq:
        """更新 FAQ 内容并刷新规范化哈希。"""
        normalized_question = question.strip()
        normalized_answer = answer.strip()
        if not normalized_question or not normalized_answer:
            raise ValueError("faq question and answer must not be empty")
        async with self._session_factory() as session:
            faq = await session.get(FaqModel, faq_id)
            if faq is None:
                raise LookupError(f"faq not found: {faq_id}")
            faq.standard_question = normalized_question
            faq.normalized_hash = self.question_hash(normalized_question)
            faq.answer_text = normalized_answer
            await session.commit()
            await session.refresh(faq)
            return self._to_faq(faq)

    # 作用：启用或停用已发布 FAQ。
    async def set_published_status(self, faq_id: str, status: str, operator_id: str) -> Faq:
        """更新 FAQ 状态。"""
        if status not in {"published", "disabled"}:
            raise ValueError("faq status must be published or disabled")
        async with self._session_factory() as session:
            faq = await session.get(FaqModel, faq_id)
            if faq is None:
                raise LookupError(f"faq not found: {faq_id}")
            faq.status = status
            await session.commit()
            await session.refresh(faq)
            return self._to_faq(faq)

    # 作用：驳回候选 FAQ。
    async def reject_candidate(self, candidate_id: str, operator_id: str, reason: str) -> None:
        """更新候选为已驳回。"""
        async with self._session_factory() as session:
            candidate = await session.get(FaqCandidateModel, candidate_id)
            if candidate is None:
                raise LookupError(f"faq candidate not found: {candidate_id}")
            candidate.status = FaqCandidateStatus.REJECTED.value
            candidate.reviewed_by = operator_id
            candidate.reject_reason = reason
            await session.commit()

    # 作用：标准化问题并计算 SHA-256 哈希。
    @staticmethod
    def question_hash(question: str) -> str:
        """返回问题哈希。"""
        normalized = re.sub(r"\s+", " ", question.strip().casefold())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    # 作用：将 ORM 候选转换为领域模型。
    @staticmethod
    def _to_candidate(row: FaqCandidateModel) -> FaqCandidate:
        """转换候选模型。"""
        return FaqCandidate(
            candidate_id=row.candidate_id,
            representative_question=row.representative_question,
            standard_answer=row.standard_answer,
            frequency=row.frequency,
            distinct_users=row.distinct_users,
            permission_signature=row.permission_signature,
            status=FaqCandidateStatus(row.status),
            confidence=row.confidence,
        )

    # 作用：将 ORM FAQ 转换为领域模型。
    @staticmethod
    def _to_faq(row: FaqModel) -> Faq:
        """转换 FAQ 模型。"""
        return Faq(
            faq_id=row.faq_id,
            standard_question=row.standard_question,
            answer_text=row.answer_text,
            status=row.status,
            knowledge_id=row.knowledge_id or "",
            version_id=row.version_id or "",
            updated_at=row.updated_at,
        )

    # 作用：构造领域权限规则。
    @staticmethod
    def _to_grant(scope: str, subject_id: str, include_descendants: bool) -> PermissionGrant:
        """转换权限规则。"""
        return PermissionGrant(
            scope=PermissionScope(scope),
            subject_id=subject_id,
            include_descendants=include_descendants,
        )