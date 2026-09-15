"""定义查询流程节点基类。"""

from abc import ABC, abstractmethod
from typing import Any

from kb_manage_platform.engines.query_engine.state import QaGraphState
from kb_manage_platform.common.logger import logger


class QueryNodeBase(ABC):
    """查询节点基类，统一日志和异常处理。"""

    name = "query_node_base"

    # 作用：执行节点并统一记录异常。
    async def __call__(self, state: QaGraphState) -> dict[str, Any]:
        """执行节点。"""
        try:
            logger.info("query node start: %s", self.name)
            return await self.process(state)
        except Exception:
            logger.exception("query node failed: %s", self.name)
            raise

    # 作用：定义子类必须实现的核心处理逻辑。
    @abstractmethod
    async def process(self, state: QaGraphState) -> dict[str, Any]:
        """处理节点逻辑。"""
        raise NotImplementedError