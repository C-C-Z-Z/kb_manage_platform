"""发布知识单元。"""

from typing import Any

from kb_manage_platform.domain.models import KnowledgeStatus, VersionStatus
from kb_manage_platform.domain.ports import KnowledgeRepositoryPort
from kb_manage_platform.engines.knowledge_engine.base import KnowledgeNodeBase
from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState


class NodePublishKnowledge(KnowledgeNodeBase):
    """确认当前版本已索引后发布知识。"""

    name = "node_publish_knowledge"

    # 作用：保存知识仓储端口。
    def __init__(self, repository: KnowledgeRepositoryPort) -> None:
        self._repository = repository

    # 作用：校验当前版本并更新发布状态。
    async def process(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """返回已发布知识单元。"""
        command = state["command"]
        current = state["knowledge"]
        version = await self._repository.get_current_version(current.knowledge_id)
        if version is None or version.status is not VersionStatus.INDEXED:
            raise ValueError("current version is not indexed")
        knowledge = await self._repository.set_unit_status(
            current.knowledge_id, KnowledgeStatus.PUBLISHED, command.operator_id
        )
        return {"knowledge": knowledge, "version": version}