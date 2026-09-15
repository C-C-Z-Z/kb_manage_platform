"""提供 FAQ 与知识缺口闭环应用服务。"""

from uuid import uuid4

from kb_manage_platform.domain.models import (
    Faq,
    FaqCandidate,
    FaqCandidateStatus,
    FaqGapAction,
    FaqGapCommand,
    FaqGapResult,
    KnowledgeGap,
    KnowledgeGapStatus,
    PermissionGrant,
)
from kb_manage_platform.domain.ports import (
    FaqCacheInvalidationPort,
    FaqManagementRepositoryPort,
    KnowledgeGapRepositoryPort,
)
from kb_manage_platform.engines.faq_gap_engine.main_graph import FaqGapWorkflow


class FaqGapService:
    """编排 FAQ 沉淀和知识缺口闭环用例。"""

    # 作用：注入 FAQ 仓储、缺口仓储和工作流。
    def __init__(
        self,
        workflow: FaqGapWorkflow,
        faq_repository: FaqManagementRepositoryPort,
        gap_repository: KnowledgeGapRepositoryPort,
        faq_cache: FaqCacheInvalidationPort | None = None,
    ) -> None:
        self._workflow = workflow
        self._faq_repository = faq_repository
        self._gap_repository = gap_repository
        self._faq_cache = faq_cache

    # 作用：执行 FAQ 挖掘。
    async def mine_faq(self, operator_id: str, window_days: int = 30) -> FaqGapResult:
        """触发 FAQ 聚类和候选生成。"""
        return await self._run(FaqGapAction.MINE_FAQ, operator_id, window_days=window_days)

    # 作用：执行 FAQ 候选审核。
    async def review_faq(
        self,
        candidate_id: str,
        question: str,
        decision: str,
        operator_id: str,
        grants: tuple[PermissionGrant, ...] = (),
        reason: str = "",
    ) -> FaqGapResult:
        """发布或驳回 FAQ 候选。"""
        return await self._run(
            FaqGapAction.REVIEW_FAQ,
            operator_id,
            candidate_id=candidate_id,
            question=question,
            decision=decision,
            grants=grants,
            reason=reason,
        )

    # 作用：执行知识缺口识别和聚合。
    async def detect_gaps(self, operator_id: str, window_days: int = 30) -> FaqGapResult:
        """触发知识缺口识别。"""
        return await self._run(FaqGapAction.DETECT_GAPS, operator_id, window_days=window_days)

    # 作用：将知识缺口转为补充草稿。
    async def convert_gap(self, gap_id: str, title: str, category_id: str, operator_id: str) -> FaqGapResult:
        """创建知识补充草稿。"""
        return await self._run(
            FaqGapAction.CONVERT_GAP,
            operator_id,
            gap_id=gap_id,
            title=title,
            category_id=category_id,
        )

    # 作用：解决或忽略知识缺口。
    async def resolve_gap(self, gap_id: str, operator_id: str, decision: str = "resolve", reason: str = "") -> FaqGapResult:
        """更新知识缺口状态。"""
        return await self._run(
            FaqGapAction.RESOLVE_GAP,
            operator_id,
            gap_id=gap_id,
            decision=decision,
            reason=reason,
        )

    # 作用：查询 FAQ 候选。
    async def list_candidates(self, status: FaqCandidateStatus | None = None) -> tuple[FaqCandidate, ...]:
        """返回 FAQ 候选列表。"""
        return await self._faq_repository.list_candidates(status)  # type: ignore

    # 作用：查询已发布 FAQ 管理列表。
    async def list_published_faqs(self) -> tuple[Faq, ...]:
        """返回已发布和停用的 FAQ。"""
        return await self._faq_repository.list_published()  # type: ignore

    # 作用：更新已发布 FAQ 内容。
    async def update_published_faq(
        self, faq_id: str, question: str, answer: str, operator_id: str
    ) -> Faq:
        """更新 FAQ 内容。"""
        previous = next(
            (item for item in await self._faq_repository.list_published() if item.faq_id == faq_id),
            None,
        )
        item = await self._faq_repository.update_published(  # type: ignore
            faq_id, question, answer, operator_id
        )
        if self._faq_cache is not None:
            if previous is not None:
                await self._faq_cache.invalidate_question(previous.standard_question)
            await self._faq_cache.invalidate_question(item.standard_question)
        return item

    # 作用：启用或停用已发布 FAQ。
    async def set_published_faq_status(
        self, faq_id: str, status: str, operator_id: str
    ) -> Faq:
        """更新 FAQ 可用状态。"""
        item = await self._faq_repository.set_published_status(  # type: ignore
            faq_id, status, operator_id
        )
        if self._faq_cache is not None:
            await self._faq_cache.invalidate_question(item.standard_question)
        return item

    # 作用：查询知识缺口。
    async def list_gaps(self, status: KnowledgeGapStatus | None = None) -> tuple[KnowledgeGap, ...]:
        """返回知识缺口列表。"""
        return await self._gap_repository.list_gaps(status)  # type: ignore

    # 作用：创建命令并执行工作流。
    async def _run(self, action: FaqGapAction, operator_id: str, **payload) -> FaqGapResult:
        """执行 FAQ/缺口工作流。"""
        command = FaqGapCommand(
            action=action,
            request_id=str(uuid4()),
            operator_id=operator_id,
            **payload,
        )
        state = await self._workflow.ainvoke({"command": command})
        return state["result"]