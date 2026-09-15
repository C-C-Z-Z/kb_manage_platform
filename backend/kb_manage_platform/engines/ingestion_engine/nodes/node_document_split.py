"""实现 Markdown 切片节点。"""

from typing import Any

from kb_manage_platform.domain.ports import ChunkerPort
from kb_manage_platform.engines.ingestion_engine.base import ImportNodeBase
from kb_manage_platform.engines.ingestion_engine.state import IngestionGraphState


class NodeDocumentSplit(ImportNodeBase):
    """将正文和图片摘要切分为知识切片。"""

    name = "node_document_split"

    # 作用：保存切片端口。
    def __init__(self, chunker: ChunkerPort) -> None:
        self._chunker = chunker

    # 作用：执行结构化切片。
    async def process(self, state: IngestionGraphState) -> dict[str, Any]:
        """返回知识切片。"""
        request = state["request"]
        chunks = await self._chunker.chunk(
            state.get("markdown", ""),
            state.get("image_summaries", []),
            request.knowledge_id,
            request.version_id,
        )
        return {"chunks": list(chunks)}