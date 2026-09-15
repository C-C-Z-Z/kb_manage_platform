"""验证文档版本任务包含 Worker 执行所需的完整字段。"""

from types import SimpleNamespace

import pytest

from kb_manage_platform.domain.models import KnowledgeAction, KnowledgeMaintenanceCommand, KnowledgeVersion
from kb_manage_platform.engines.ingestion_engine.nodes.node_entry import NodeEntry
from kb_manage_platform.engines.knowledge_engine.nodes.node_create_version import NodeCreateVersion


class FakeKnowledgeRepository:
    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        return version


class FakeJobRepository:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    async def enqueue(self, job_type, payload, idempotency_key) -> str:
        self.payloads.append(dict(payload))
        return "job-1"


@pytest.mark.asyncio
async def test_create_version_enqueues_worker_payload_fields() -> None:
    job_repository = FakeJobRepository()
    node = NodeCreateVersion(FakeKnowledgeRepository(), job_repository)  # type: ignore[arg-type]
    command = KnowledgeMaintenanceCommand(
        action=KnowledgeAction.CREATE_VERSION,
        request_id="request-1",
        operator_id="user-admin",
        knowledge_id="knowledge-1",
        source_object_key="knowledge/knowledge-1/version-1/manual.md",
        filename="manual.md",
        content_type="text/markdown",
    )

    result = await node.process(
        {
            "command": command,
            "knowledge": SimpleNamespace(knowledge_id="knowledge-1"),
        }
    )

    payload = job_repository.payloads[0]
    assert result["job_id"] == "job-1"
    assert payload["request_id"] == "request-1"
    assert payload["user_id"] == "user-admin"
    assert payload["knowledge_id"] == "knowledge-1"
    assert payload["version_id"] == result["version"].version_id
    assert payload["original_object_key"] == command.source_object_key
    assert payload["filename"] == "manual.md"
    assert payload["content_type"] == "text/markdown"

@pytest.mark.asyncio
async def test_ingestion_entry_accepts_markdown() -> None:
    node = NodeEntry()
    result = await node.process({"request": SimpleNamespace(filename="manual.md")})
    assert result == {"markdown": ""}