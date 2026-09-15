"""标记版本文档已经完成索引。"""

from typing import Any

from kb_manage_platform.domain.ports import DocumentRepositoryPort
from kb_manage_platform.engines.ingestion_engine.base import ImportNodeBase
from kb_manage_platform.engines.ingestion_engine.state import IngestionGraphState


class NodeIndexVersion(ImportNodeBase):
    """将当前版本文档更新为已索引，等待人工发布。"""

    name = "node_index_version"

    # 作用：保存知识仓储端口。
    def __init__(self, repository: DocumentRepositoryPort) -> None:
        self._repository = repository

    # 作用：更新版本状态为 indexed。
    async def process(self, state: IngestionGraphState) -> dict[str, Any]:
        """返回索引状态。"""
        request = state["request"]
        await self._repository.save_version(
            request.request_id, request.knowledge_id, request.version_id, "indexed"
        )
        return {"indexed": True}