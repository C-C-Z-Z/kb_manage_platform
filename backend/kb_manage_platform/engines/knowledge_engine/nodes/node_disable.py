"""停用知识单元。"""

from typing import Any

from kb_manage_platform.domain.models import KnowledgeAction, KnowledgeStatus
from kb_manage_platform.domain.ports import KnowledgeRepositoryPort
from kb_manage_platform.engines.knowledge_engine.base import KnowledgeNodeBase
from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState


class NodeDisableKnowledge(KnowledgeNodeBase):
    """执行知识停用。"""

    name = "node_disable_knowledge"

    # 作用：保存知识仓储端口。
    def __init__(self, repository: KnowledgeRepositoryPort) -> None:
        self._repository = repository

    # 作用：更新知识单元为停用状态。
    async def process(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """返回停用后的知识单元。"""
        command = state["command"]
        target = (
            KnowledgeStatus.ARCHIVED
            if command.action is KnowledgeAction.ARCHIVE
            else KnowledgeStatus.DISABLED
        )
        knowledge = await self._repository.set_unit_status(
            state["knowledge"].knowledge_id, target, command.operator_id
        )
        return {"knowledge": knowledge}

