"""创建知识新版本并提交入库任务。"""

from typing import Any
from uuid import uuid4

from kb_manage_platform.domain.models import KnowledgeVersion, VersionStatus
from kb_manage_platform.domain.ports import JobRepositoryPort, KnowledgeRepositoryPort
from kb_manage_platform.engines.knowledge_engine.base import KnowledgeNodeBase
from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState


class NodeCreateVersion(KnowledgeNodeBase):
    """创建版本文档并投递 MySQL 后台任务。"""

    name = "node_create_version"

    # 作用：保存知识仓储和任务仓储。
    def __init__(self, repository: KnowledgeRepositoryPort, job_repository: JobRepositoryPort) -> None:
        self._repository = repository
        self._job_repository = job_repository

    # 作用：创建版本并写入解析任务。
    async def process(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """返回版本和任务 ID。"""
        command = state["command"]
        knowledge = state["knowledge"]
        version = KnowledgeVersion(
            version_id=str(uuid4()),
            knowledge_id=knowledge.knowledge_id,
            version_no=0,
            source_object_key=command.source_object_key,
            filename=command.filename,
            content_type=command.content_type,
            status=VersionStatus.PROCESSING,
            created_by=command.operator_id,
        )
        saved = await self._repository.create_version(version)
        job_id = await self._job_repository.enqueue(
            "ingest_document",
            {
                "request_id": command.request_id,
                "user_id": command.operator_id,
                "knowledge_id": knowledge.knowledge_id,
                "version_id": saved.version_id,
                "original_object_key": saved.source_object_key,
                "filename": saved.filename,
                "content_type": saved.content_type,
            },
            idempotency_key=f"{knowledge.knowledge_id}:{saved.version_id}",
        )
        return {"version": saved, "job_id": job_id}