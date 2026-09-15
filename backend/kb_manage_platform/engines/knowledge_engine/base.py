"""定义知识维护节点基类。"""

from abc import ABC, abstractmethod
from typing import Any

from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState
from kb_manage_platform.common.logger import logger


class KnowledgeNodeBase(ABC):
    """知识维护节点基类。"""

    name = "knowledge_node_base"

    # 作用：统一执行节点并记录异常。
    async def __call__(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """执行知识维护节点。"""
        try:
            logger.info("knowledge node start: %s", self.name)
            return await self.process(state)
        except Exception:
            logger.exception("knowledge node failed: %s", self.name)
            raise

    # 作用：定义子类必须实现的核心逻辑。
    @abstractmethod
    async def process(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """处理节点逻辑。"""
        raise NotImplementedError