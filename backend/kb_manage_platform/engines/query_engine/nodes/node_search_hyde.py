"""实现 LangChain LLM HyDE 与 Milvus 向量检索节点。"""

from typing import Any

from kb_manage_platform.domain.ports import HydeGeneratorPort, VectorRetrieverPort
from kb_manage_platform.engines.query_engine.base import QueryNodeBase
from kb_manage_platform.engines.query_engine.state import QaGraphState


class NodeSearchHyde(QueryNodeBase):
    """执行路线 B HyDE 检索。"""

    name = "node_search_hyde"

    # 作用：保存 HyDE 生成器、向量检索端口和参数。
    def __init__(
        self,
        generator: HydeGeneratorPort,
        retriever: VectorRetrieverPort,
        hyde_count: int,
        top_k: int,
    ) -> None:
        self._generator = generator
        self._retriever = retriever
        self._hyde_count = hyde_count
        self._top_k = top_k

    # 作用：生成 HyDE 文档并执行向量检索。
    async def process(self, state: QaGraphState) -> dict[str, Any]:
        """返回路线 B 候选。"""
        try:
            texts = await self._generator.generate(state["normalized_question"], self._hyde_count)
            candidates = await self._retriever.retrieve(texts, state["request"].user, self._top_k)
        except Exception:
            return {"hyde_candidates": [], "warnings": ["hyde_retrieval_unavailable"]}
        return {"hyde_candidates": list(candidates)}