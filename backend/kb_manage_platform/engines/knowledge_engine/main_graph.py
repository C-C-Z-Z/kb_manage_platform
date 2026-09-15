"""装配知识维护与四维权限配置 LangGraph。"""

from typing import Any

from langgraph.graph import END, StateGraph

from kb_manage_platform.domain.models import KnowledgeAction
from kb_manage_platform.domain.ports import (
    AuditPort,
    JobRepositoryPort,
    KnowledgePermissionRepositoryPort,
    KnowledgeRepositoryPort,
    PermissionVersionPort,
)
from kb_manage_platform.domain.services.permissions import PermissionPolicy
from kb_manage_platform.engines.knowledge_engine.nodes.node_audit import NodeKnowledgeAudit
from kb_manage_platform.engines.knowledge_engine.nodes.node_create_version import NodeCreateVersion
from kb_manage_platform.engines.knowledge_engine.nodes.node_disable import NodeDisableKnowledge
from kb_manage_platform.engines.knowledge_engine.nodes.node_entry import NodeKnowledgeEntry
from kb_manage_platform.engines.knowledge_engine.nodes.node_load_or_create import NodeLoadOrCreate
from kb_manage_platform.engines.knowledge_engine.nodes.node_publish import NodePublishKnowledge
from kb_manage_platform.engines.knowledge_engine.nodes.node_save_permissions import NodeSavePermissions
from kb_manage_platform.engines.knowledge_engine.nodes.node_update_metadata import NodeUpdateMetadata
from kb_manage_platform.engines.knowledge_engine.nodes.node_validate_permissions import NodeValidatePermissions
from kb_manage_platform.engines.knowledge_engine.state import KnowledgeGraphState


class KnowledgeMaintenanceWorkflow:
    """知识维护和权限配置工作流。"""

    # 作用：保存依赖并初始化工作流节点。
    def __init__(
        self,
        repository: KnowledgeRepositoryPort,
        permission_repository: KnowledgePermissionRepositoryPort,
        permission_version: PermissionVersionPort,
        job_repository: JobRepositoryPort,
        audit: AuditPort,
        permission_policy: PermissionPolicy,
    ) -> None:
        self._workflow = StateGraph(KnowledgeGraphState)
        self._compiled_app: Any = None
        self._init_nodes(
            repository,
            permission_repository,
            permission_version,
            job_repository,
            audit,
            permission_policy,
        )
        self._register_nodes()
        self._setup_routes()

    # 作用：创建各知识维护节点。
    def _init_nodes(
        self,
        repository: KnowledgeRepositoryPort,
        permission_repository: KnowledgePermissionRepositoryPort,
        permission_version: PermissionVersionPort,
        job_repository: JobRepositoryPort,
        audit: AuditPort,
        permission_policy: PermissionPolicy,
    ) -> None:
        """初始化节点对象。"""
        self.node_entry = NodeKnowledgeEntry()
        self.node_load_or_create = NodeLoadOrCreate(repository)
        self.node_update_metadata = NodeUpdateMetadata(repository)
        self.node_create_version = NodeCreateVersion(repository, job_repository)
        self.node_validate_permissions = NodeValidatePermissions(permission_policy)
        self.node_save_permissions = NodeSavePermissions(permission_repository, permission_version)
        self.node_publish = NodePublishKnowledge(repository)
        self.node_disable = NodeDisableKnowledge(repository)
        self.node_audit = NodeKnowledgeAudit(audit)

    # 作用：注册知识维护节点。
    def _register_nodes(self) -> None:
        """注册节点到 LangGraph。"""
        self._workflow.add_node("node_entry", self.node_entry)
        self._workflow.add_node("node_load_or_create", self.node_load_or_create)
        self._workflow.add_node("node_update_metadata", self.node_update_metadata)
        self._workflow.add_node("node_create_version", self.node_create_version)
        self._workflow.add_node("node_validate_permissions", self.node_validate_permissions)
        self._workflow.add_node("node_save_permissions", self.node_save_permissions)
        self._workflow.add_node("node_publish", self.node_publish)
        self._workflow.add_node("node_disable", self.node_disable)
        self._workflow.add_node("node_audit", self.node_audit)

    # 作用：按维护动作选择后续节点。
    def _route_by_action(self, state: KnowledgeGraphState) -> str:
        """返回动作对应节点名称。"""
        action = state["command"].action
        routes = {
            KnowledgeAction.CREATE: "node_audit",
            KnowledgeAction.UPDATE_METADATA: "node_update_metadata",
            KnowledgeAction.CREATE_VERSION: "node_create_version",
            KnowledgeAction.CONFIGURE_PERMISSIONS: "node_validate_permissions",
            KnowledgeAction.PUBLISH: "node_publish",
            KnowledgeAction.DISABLE: "node_disable",
            KnowledgeAction.ARCHIVE: "node_disable",
        }
        return routes[action]

    # 作用：配置工作流路由。
    def _setup_routes(self) -> None:
        """设置知识维护边。"""
        self._workflow.set_entry_point("node_entry")
        self._workflow.add_edge("node_entry", "node_load_or_create")
        self._workflow.add_conditional_edges(
            "node_load_or_create",
            self._route_by_action,
            {
                "node_audit": "node_audit",
                "node_update_metadata": "node_update_metadata",
                "node_create_version": "node_create_version",
                "node_validate_permissions": "node_validate_permissions",
                "node_publish": "node_publish",
                "node_disable": "node_disable",
            },
        )
        for node_name in (
            "node_update_metadata",
            "node_create_version",
            "node_publish",
            "node_disable",
        ):
            self._workflow.add_edge(node_name, "node_audit")
        self._workflow.add_edge("node_validate_permissions", "node_save_permissions")
        self._workflow.add_edge("node_save_permissions", "node_audit")
        self._workflow.add_edge("node_audit", END)

    # 作用：懒加载编译工作流。
    def compile(self) -> Any:
        """编译并返回工作流。"""
        if self._compiled_app is None:
            self._compiled_app = self._workflow.compile()
        return self._compiled_app

    # 作用：执行知识维护工作流。
    async def ainvoke(self, initial_state: KnowledgeGraphState) -> KnowledgeGraphState:
        """返回工作流最终状态。"""
        return await self.compile().ainvoke(initial_state)
