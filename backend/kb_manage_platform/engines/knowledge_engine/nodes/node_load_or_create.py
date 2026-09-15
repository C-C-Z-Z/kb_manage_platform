"""加载现有知识单元或创建新草稿。"""

from typing import Any

from kb_manage_platform.domain.models import KnowledgeAction
from kb_manage_platform.domain.ports import KnowledgeRepositoryPort
from kb_manage_platform.engines.knowledge_engine.base import KnowledgeNodeBase
from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState


class NodeLoadOrCreate(KnowledgeNodeBase):
    """根据动作加载或创建知识单元。"""

    name = "node_load_or_create"

    # 作用：保存知识仓储端口。
    def __init__(self, repository: KnowledgeRepositoryPort) -> None:
        self._repository = repository

    # 作用：创建草稿或读取已有知识单元。
    async def process(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """返回知识单元状态。"""
        command = state["command"]
        if command.action is KnowledgeAction.CREATE:
            knowledge = await self._repository.create_unit(command)
        else:
            knowledge = await self._repository.get_unit(command.knowledge_id)
            if knowledge is None:
                raise LookupError(f"knowledge not found: {command.knowledge_id}")
        return {"knowledge": knowledge}