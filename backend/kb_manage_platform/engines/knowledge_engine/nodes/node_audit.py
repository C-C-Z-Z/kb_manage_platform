"""生成知识维护结果并写入审计。"""

from typing import Any

from kb_manage_platform.domain.models import KnowledgeMaintenanceResult
from kb_manage_platform.domain.ports import AuditPort
from kb_manage_platform.engines.knowledge_engine.base import KnowledgeNodeBase
from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState


class NodeKnowledgeAudit(KnowledgeNodeBase):
    """记录知识维护动作并组装结果。"""

    name = "node_knowledge_audit"

    # 作用：保存审计端口。
    def __init__(self, audit: AuditPort) -> None:
        self._audit = audit

    # 作用：写入审计并返回最终结果。
    async def process(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """返回工作流结果。"""
        command = state["command"]
        knowledge = state["knowledge"]
        version = state.get("version")
        result = KnowledgeMaintenanceResult(
            knowledge_id=knowledge.knowledge_id,
            status=knowledge.status,
            version_id=version.version_id if version else "",
            job_id=state.get("job_id", ""),
            permission_version=state.get("permission_version", 0),
        )
        await self._audit.record(
            f"knowledge.{command.action.value}",
            {
                "request_id": command.request_id,
                "operator_id": command.operator_id,
                "knowledge_id": knowledge.knowledge_id,
                "status": knowledge.status.value,
                "job_id": result.job_id,
            },
        )
        return {"result": result}