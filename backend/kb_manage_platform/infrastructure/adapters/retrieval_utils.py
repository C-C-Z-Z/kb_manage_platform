"""实现 Milvus 双路检索适配器。"""

from collections.abc import Sequence

from kb_manage_platform.domain.models import RetrievedCandidate, UserContext
from kb_manage_platform.domain.ports import EmbedderPort
from kb_manage_platform.infrastructure.adapters.milvus_utils import MilvusStore


class MilvusHybridRetriever:
    """路线 A：Dense Vector、BM25 与关键词的 Milvus 原生混合检索。"""

    # 作用：注入共享 Milvus 存储和 Embedding 端口。
    def __init__(self, store: MilvusStore, embedder: EmbedderPort) -> None:
        self._store = store
        self._embedder = embedder

    # 作用：执行原文混合检索。
    async def retrieve(
        self,
        question: str,
        user: UserContext,
        top_k: int,
    ) -> Sequence[RetrievedCandidate]:
        """返回原文 BM25 与 Dense Vector 融合候选。"""
        vectors = await self._embedder.embed([question])
        if not vectors:
            return []
        return await self._store.hybrid_search(vectors[0], question, top_k)


class MilvusVectorRetriever:
    """路线 B：对 HyDE 文档执行 Dense Vector 语义检索。"""

    # 作用：注入共享 Milvus 存储和 Embedding 端口。
    def __init__(self, store: MilvusStore, embedder: EmbedderPort) -> None:
        self._store = store
        self._embedder = embedder

    # 作用：执行 HyDE 语义检索。
    async def retrieve(
        self,
        texts: Sequence[str],
        user: UserContext,
        top_k: int,
    ) -> Sequence[RetrievedCandidate]:
        """返回多个 HyDE 文档的语义候选并去重。"""
        if not texts:
            return []
        vectors = await self._embedder.embed(texts)
        candidates: dict[str, RetrievedCandidate] = {}
        for vector in vectors:
            for candidate in await self._store.search_dense(vector, top_k):
                existing = candidates.get(candidate.chunk_id)
                if existing is None or candidate.score > existing.score:
                    candidates[candidate.chunk_id] = candidate
        return sorted(candidates.values(), key=lambda item: item.score, reverse=True)[:top_k]