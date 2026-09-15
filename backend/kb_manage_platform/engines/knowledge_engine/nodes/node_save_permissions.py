"""保存四维权限并使缓存失效。"""

from typing import Any

from kb_manage_platform.domain.ports import KnowledgePermissionRepositoryPort, PermissionVersionPort
from kb_manage_platform.engines.knowledge_engine.base import KnowledgeNodeBase
from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState


class NodeSavePermissions(KnowledgeNodeBase):
    """写入权限规则并递增权限版本。"""

    name = "node_save_permissions"

    # 作用：保存权限仓储和版本端口。
    def __init__(self, repository: KnowledgePermissionRepositoryPort, permission_version: PermissionVersionPort) -> None:
        self._repository = repository
        self._permission_version = permission_version

    # 作用：替换权限规则并失效缓存。
    async def process(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """返回权限版本。"""
        command = state["command"]
        knowledge = state["knowledge"]
        permission_set = await self._repository.replace_grants(
            knowledge.knowledge_id, state.get("grants", ()), command.operator_id
        )
        version = await self._permission_version.invalidate(knowledge.knowledge_id)
        return {"permission_version": version, "grants": permission_set.grants}