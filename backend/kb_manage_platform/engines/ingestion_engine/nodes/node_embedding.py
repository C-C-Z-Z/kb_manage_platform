"""实现 Embedding 向量化节点。"""

from typing import Any

from kb_manage_platform.domain.ports import EmbedderPort
from kb_manage_platform.engines.ingestion_engine.base import ImportNodeBase
from kb_manage_platform.engines.ingestion_engine.state import IngestionGraphState


class NodeEmbedding(ImportNodeBase):
    """为知识切片批量生成 Dense Vector。"""

    name = "node_embedding"

    # 作用：保存 Embedding 端口。
    def __init__(self, embedder: EmbedderPort) -> None:
        self._embedder = embedder

    # 作用：执行批量向量化。
    async def process(self, state: IngestionGraphState) -> dict[str, Any]:
        """返回向量列表。"""
        chunks = state.get("chunks", [])
        vectors = await self._embedder.embed([chunk.content for chunk in chunks])
        return {"vectors": [list(vector) for vector in vectors]}