"""定义 FAQ 与知识缺口节点基类。"""

from abc import ABC, abstractmethod
from typing import Any

from kb_manage_platform.common.logger import logger
from kb_manage_platform.engines.faq_gap_engine.state import FaqGapGraphState


class FaqGapNodeBase(ABC):
    """FAQ 与知识缺口节点基类。"""

    name = "faq_gap_node_base"

    # 作用：统一执行节点并记录异常。
    async def __call__(self, state: FaqGapGraphState) -> dict[str, Any]:
        """执行节点。"""
        try:
            logger.info("faq/gap node start: %s", self.name)
            return await self.process(state)
        except Exception:
            logger.exception("faq/gap node failed: %s", self.name)
            raise

    # 作用：定义子类必须实现的核心逻辑。
    @abstractmethod
    async def process(self, state: FaqGapGraphState) -> dict[str, Any]:
        """处理节点逻辑。"""
        raise NotImplementedError