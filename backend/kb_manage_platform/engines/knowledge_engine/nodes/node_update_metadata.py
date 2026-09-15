"""更新知识单元标题、分类和标签。"""

from typing import Any

from kb_manage_platform.domain.ports import KnowledgeRepositoryPort
from kb_manage_platform.engines.knowledge_engine.base import KnowledgeNodeBase
from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState


class NodeUpdateMetadata(KnowledgeNodeBase):
    """执行知识元数据更新。"""

    name = "node_update_metadata"

    # 作用：保存知识仓储端口。
    def __init__(self, repository: KnowledgeRepositoryPort) -> None:
        self._repository = repository

    # 作用：更新知识单元元数据。
    async def process(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """返回更新后的知识单元。"""
        command = state["command"]
        current = state["knowledge"]
        knowledge = await self._repository.update_metadata(
            knowledge_id=current.knowledge_id,
            title=command.title or current.title,
            category_id=command.category_id or current.category_id,
            tags=command.tags or current.tags,
            operator_id=command.operator_id,
        )
        return {"knowledge": knowledge}