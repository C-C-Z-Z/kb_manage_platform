"""将知识缺口转为知识补充草稿。"""

from typing import Any

from kb_manage_platform.domain.models import KnowledgeAction, KnowledgeMaintenanceCommand
from kb_manage_platform.domain.ports import KnowledgeGapRepositoryPort, KnowledgeRepositoryPort
from kb_manage_platform.engines.faq_gap_engine.base import FaqGapNodeBase
from kb_manage_platform.engines.faq_gap_engine.state import FaqGapGraphState


class NodeConvertGap(FaqGapNodeBase):
    """创建知识补充草稿并关联知识缺口。"""

    name = "node_convert_gap"

    # 作用：保存知识仓储和缺口仓储。
    def __init__(self, knowledge_repository: KnowledgeRepositoryPort, gap_repository: KnowledgeGapRepositoryPort) -> None:
        self._knowledge_repository = knowledge_repository
        self._gap_repository = gap_repository

    # 作用：创建知识草稿并建立缺口关联。
    async def process(self, state: FaqGapGraphState) -> dict[str, Any]:
        """返回草稿 ID。"""
        command = state["command"]
        gap = await self._gap_repository.get_gap(command.gap_id)
        if gap is None:
            raise LookupError(f"knowledge gap not found: {command.gap_id}")
        knowledge = await self._knowledge_repository.create_unit(
            KnowledgeMaintenanceCommand(
                action=KnowledgeAction.CREATE,
                request_id=command.request_id,
                operator_id=command.operator_id,
                title=command.title or gap.representative_question,
                category_id=command.category_id or gap.suggested_category or "pending",
            )
        )
        draft_id = await self._gap_repository.create_supplement_draft(
            command.gap_id,
            knowledge.title,
            knowledge.category_id,
            knowledge.knowledge_id,
            command.operator_id,
        )
        return {"draft_id": draft_id, "gaps": (gap,)}