"""实现 Milvus 索引写入节点。"""

from typing import Any

from kb_manage_platform.domain.ports import VectorIndexPort
from kb_manage_platform.engines.ingestion_engine.base import ImportNodeBase
from kb_manage_platform.engines.ingestion_engine.state import IngestionGraphState


class MilvusImportNode(ImportNodeBase):
    """将切片、Dense Vector 和 BM25 数据写入 Milvus。"""

    name = "node_milvus_import"

    # 作用：保存 Milvus 索引端口。
    def __init__(self, vector_index: VectorIndexPort) -> None:
        self._vector_index = vector_index

    # 作用：执行 Milvus upsert。
    async def process(self, state: IngestionGraphState) -> dict[str, Any]:
        """返回向量 ID 列表。"""
        chunks = state.get("chunks", [])
        await self._vector_index.upsert(chunks, state.get("vectors", []))
        return {"vector_ids": [chunk.chunk_id for chunk in chunks]}