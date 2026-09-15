"""手动解决或忽略知识缺口。"""

from typing import Any

from kb_manage_platform.domain.models import KnowledgeGapStatus
from kb_manage_platform.domain.ports import KnowledgeGapRepositoryPort
from kb_manage_platform.engines.faq_gap_engine.base import FaqGapNodeBase
from kb_manage_platform.engines.faq_gap_engine.state import FaqGapGraphState


class NodeResolveGap(FaqGapNodeBase):
    """更新知识缺口状态。"""

    name = "node_resolve_gap"

    # 作用：保存缺口仓储。
    def __init__(self, repository: KnowledgeGapRepositoryPort) -> None:
        self._repository = repository

    # 作用：将缺口标记为已解决或已忽略。
    async def process(self, state: FaqGapGraphState) -> dict[str, Any]:
        """返回缺口状态。"""
        command = state["command"]
        status = KnowledgeGapStatus.IGNORED if command.decision == "ignore" else KnowledgeGapStatus.RESOLVED
        await self._repository.set_status(command.gap_id, status, command.reason)
        return {}