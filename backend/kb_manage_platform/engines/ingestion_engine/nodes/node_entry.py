"""实现文档入库入口节点。"""

from pathlib import Path
from typing import Any

from kb_manage_platform.engines.ingestion_engine.base import ImportNodeBase
from kb_manage_platform.engines.ingestion_engine.state import IngestionGraphState


class NodeEntry(ImportNodeBase):
    """校验文档请求并识别文件类型。"""

    name = "node_entry"

    # 作用：验证请求并返回文件扩展名。
    async def process(self, state: IngestionGraphState) -> dict[str, Any]:
        """完成入库入口校验。"""
        request = state["request"]
        suffix = Path(request.filename).suffix.lower()
        if suffix not in {".pdf", ".doc", ".docx", ".md", ".markdown", ".txt"}:
            raise ValueError(f"unsupported file type: {suffix}")
        return {"markdown": ""}