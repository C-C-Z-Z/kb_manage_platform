"""实现线上 MinerU 解析节点。"""

from typing import Any

from kb_manage_platform.domain.ports import DocumentParserPort
from kb_manage_platform.engines.ingestion_engine.base import ImportNodeBase
from kb_manage_platform.engines.ingestion_engine.state import IngestionGraphState


class NodeMineruParse(ImportNodeBase):
    """将 Word/PDF 转换为 Markdown 并抽取图片。"""

    name = "node_mineru_parse"

    # 作用：保存 MinerU 解析端口。
    def __init__(self, parser: DocumentParserPort) -> None:
        self._parser = parser

    # 作用：调用 MinerU 解析原文件。
    async def process(self, state: IngestionGraphState) -> dict[str, Any]:
        """返回 Markdown 和图片对象键。"""
        request = state["request"]
        markdown, image_keys = await self._parser.parse(request.original_object_key, request.filename)
        return {"markdown": markdown, "image_keys": list(image_keys)}