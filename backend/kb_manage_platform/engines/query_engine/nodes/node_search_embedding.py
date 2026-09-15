"""实现原文 BM25、关键词和向量混合检索节点。"""

from typing import Any

from kb_manage_platform.domain.ports import HybridRetrieverPort
from kb_manage_platform.engines.query_engine.base import QueryNodeBase
from kb_manage_platform.engines.query_engine.state import QaGraphState


class NodeSearchEmbedding(QueryNodeBase):
    """执行路线 A 原文混合检索。"""

    name = "node_search_embedding"

    # 作用：保存混合检索端口和召回数量。
    def __init__(self, retriever: HybridRetrieverPort, top_k: int) -> None:
        self._retriever = retriever
        self._top_k = top_k

    # 作用：返回路线 A 候选。
    async def process(self, state: QaGraphState) -> dict[str, Any]:
        """执行原文混合检索。"""
        try:
            candidates = await self._retriever.retrieve(
                state["normalized_question"], state["request"].user, self._top_k
            )
        except Exception:
            return {"warnings": ["hybrid_retrieval_unavailable"]}
        return {"original_candidates": list(candidates)}