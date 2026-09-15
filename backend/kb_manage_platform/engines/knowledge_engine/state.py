"""定义知识维护与权限配置 LangGraph 状态。"""

from typing import TypedDict

from kb_manage_platform.domain.models import (
    KnowledgeMaintenanceCommand,
    KnowledgeMaintenanceResult,
    KnowledgeUnit,
    KnowledgeVersion,
    PermissionGrant,
)


class KnowledgeGraphState(TypedDict, total=False):
    """知识维护工作流状态。"""

    command: KnowledgeMaintenanceCommand
    knowledge: KnowledgeUnit
    version: KnowledgeVersion
    job_id: str
    grants: tuple[PermissionGrant, ...]
    permission_version: int
    result: KnowledgeMaintenanceResult