"""校验知识维护命令。"""

from typing import Any

from kb_manage_platform.domain.models import KnowledgeAction
from kb_manage_platform.engines.knowledge_engine.base import KnowledgeNodeBase
from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState


class NodeKnowledgeEntry(KnowledgeNodeBase):
    """检查动作和必填参数。"""

    name = "node_knowledge_entry"

    # 作用：按动作校验命令并更新状态。
    async def process(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """返回校验后的状态。"""
        command = state["command"]
        if command.action is KnowledgeAction.CREATE:
            self._require(command.title, "title")
            self._require(command.category_id, "category_id")
        else:
            self._require(command.knowledge_id, "knowledge_id")
        if command.action is KnowledgeAction.CREATE_VERSION:
            self._require(command.source_object_key, "source_object_key")
            self._require(command.filename, "filename")
            self._require(command.content_type, "content_type")
        return {}

    # 作用：校验必填字符串字段。
    @staticmethod
    def _require(value: str, name: str) -> None:
        """缺少字段时抛出异常。"""
        if not value or not value.strip():
            raise ValueError(f"{name} must not be empty")