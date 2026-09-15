"""校验并规范化四维权限。"""

from typing import Any

from kb_manage_platform.domain.services.permissions import PermissionPolicy
from kb_manage_platform.engines.knowledge_engine.base import KnowledgeNodeBase
from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState


class NodeValidatePermissions(KnowledgeNodeBase):
    """执行权限参数校验。"""

    name = "node_validate_permissions"

    # 作用：保存权限规则服务。
    def __init__(self, policy: PermissionPolicy) -> None:
        self._policy = policy

    # 作用：规范化权限规则。
    async def process(self, state: KnowledgeGraphState) -> dict[str, Any]:
        """返回规范化权限集合。"""
        grants = self._policy.normalize(state["command"].grants)
        return {"grants": grants}