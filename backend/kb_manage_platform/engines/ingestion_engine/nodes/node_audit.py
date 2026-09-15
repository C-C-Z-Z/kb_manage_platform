"""实现导入审计节点。"""

from typing import Any

from kb_manage_platform.domain.ports import AuditPort
from kb_manage_platform.engines.ingestion_engine.base import ImportNodeBase
from kb_manage_platform.engines.ingestion_engine.state import IngestionGraphState


class NodeImportAudit(ImportNodeBase):
    """记录文档入库结果。"""

    name = "node_import_audit"

    # 作用：保存审计端口。
    def __init__(self, audit: AuditPort) -> None:
        self._audit = audit

    # 作用：写入入库审计摘要。
    async def process(self, state: IngestionGraphState) -> dict[str, Any]:
        """记录处理结果。"""
        request = state["request"]
        await self._audit.record(
            "ingestion.completed",
            {
                "request_id": request.request_id,
                "knowledge_id": request.knowledge_id,
                "version_id": request.version_id,
                "image_count": len(state.get("image_keys", [])),
                "chunk_count": len(state.get("chunks", [])),
                "indexed": state.get("indexed", False),
            },
        )
        return {}