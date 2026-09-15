"""审核 FAQ 候选并发布或驳回。"""

from typing import Any

from kb_manage_platform.domain.models import FaqReviewDecision
from kb_manage_platform.domain.ports import FaqCacheInvalidationPort, FaqManagementRepositoryPort
from kb_manage_platform.engines.faq_gap_engine.base import FaqGapNodeBase
from kb_manage_platform.engines.faq_gap_engine.state import FaqGapGraphState


class NodeReviewFaq(FaqGapNodeBase):
    """执行 FAQ 人工审核。"""

    name = "node_review_faq"

    # 作用：保存 FAQ 仓储和缓存失效端口。
    def __init__(self, repository: FaqManagementRepositoryPort, cache: FaqCacheInvalidationPort) -> None:
        self._repository = repository
        self._cache = cache

    # 作用：按审核决定发布或驳回候选。
    async def process(self, state: FaqGapGraphState) -> dict[str, Any]:
        """返回处理后的候选。"""
        command = state["command"]
        if command.decision == FaqReviewDecision.APPROVE.value:
            await self._repository.publish_candidate(command.candidate_id, command.grants, command.operator_id)
            if command.question:
                await self._cache.invalidate_question(command.question)
        elif command.decision == FaqReviewDecision.REJECT.value:
            await self._repository.reject_candidate(command.candidate_id, command.operator_id, command.reason)
        else:
            raise ValueError("invalid FAQ review decision")
        return {}