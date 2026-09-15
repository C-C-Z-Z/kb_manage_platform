"""实现 FAQ 缓存查询节点。"""

from typing import Any

from kb_manage_platform.domain.ports import FaqCachePort
from kb_manage_platform.engines.query_engine.base import QueryNodeBase
from kb_manage_platform.engines.query_engine.state import QaGraphState


class NodeFaqCache(QueryNodeBase):
    """查询 Redis FAQ 缓存。"""

    name = "node_faq_cache"

    # 作用：保存 FAQ 缓存端口。
    def __init__(self, faq_cache: FaqCachePort) -> None:
        self._faq_cache = faq_cache

    # 作用：查询 FAQ 缓存并写入状态。
    async def process(self, state: QaGraphState) -> dict[str, Any]:
        """返回 FAQ 答案或空状态。"""
        request = state["request"]
        answer = await self._faq_cache.lookup(state["normalized_question"], request.user)
        return {"faq_answer": answer} if answer else {}