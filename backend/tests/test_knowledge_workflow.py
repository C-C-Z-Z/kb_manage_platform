"""验证四维权限规则和知识维护工作流。"""

from uuid import uuid4

import pytest

from kb_manage_platform.domain.models import (
    KnowledgeAction,
    KnowledgeMaintenanceCommand,
    KnowledgePermissionSet,
    KnowledgeStatus,
    KnowledgeUnit,
    KnowledgeVersion,
    JobRecord,
    PermissionGrant,
    PermissionScope,
    UserContext,
    VersionStatus,
)
from kb_manage_platform.domain.services.permissions import PermissionPolicy
from kb_manage_platform.engines.knowledge_engine.main_graph import KnowledgeMaintenanceWorkflow


class FakeKnowledgeRepository:
    """知识仓储内存实现。"""

    # 作用：初始化空仓储。
    def __init__(self) -> None:
        self.units: dict[str, KnowledgeUnit] = {}
        self.versions: dict[str, KnowledgeVersion] = {}

    # 作用：创建知识草稿。
    async def create_unit(self, command: KnowledgeMaintenanceCommand) -> KnowledgeUnit:
        """保存知识草稿。"""
        unit = KnowledgeUnit(
            knowledge_id=command.knowledge_id or str(uuid4()),
            title=command.title,
            category_id=command.category_id,
            tags=command.tags,
            status=KnowledgeStatus.DRAFT,
            created_by=command.operator_id,
            updated_by=command.operator_id,
        )
        self.units[unit.knowledge_id] = unit
        return unit

    # 作用：读取知识单元。
    async def get_unit(self, knowledge_id: str) -> KnowledgeUnit | None:
        """返回知识单元。"""
        return self.units.get(knowledge_id)

    # 作用：更新知识元数据。
    async def update_metadata(self, knowledge_id, title, category_id, tags, operator_id):
        """保存元数据更新。"""
        unit = self.units[knowledge_id]
        updated = KnowledgeUnit(
            knowledge_id=unit.knowledge_id,
            title=title,
            category_id=category_id,
            tags=tags,
            status=unit.status,
            created_by=unit.created_by,
            updated_by=operator_id,
            current_version_id=unit.current_version_id,
        )
        self.units[knowledge_id] = updated
        return updated

    # 作用：保存版本文档。
    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        """保存知识版本。"""
        saved = KnowledgeVersion(
            version_id=version.version_id,
            knowledge_id=version.knowledge_id,
            version_no=1,
            source_object_key=version.source_object_key,
            markdown_object_key=version.markdown_object_key,
            filename=version.filename,
            content_type=version.content_type,
            status=version.status,
            created_by=version.created_by,
        )
        self.versions[saved.version_id] = saved
        return saved

    # 作用：读取当前版本。
    async def get_current_version(self, knowledge_id: str) -> KnowledgeVersion | None:
        """返回第一个匹配版本。"""
        return next(
            (v for v in self.versions.values() if v.knowledge_id == knowledge_id),
            None,
        )

    # 作用：更新知识状态。
    async def set_unit_status(self, knowledge_id, status, operator_id):
        """保存状态变化。"""
        unit = self.units[knowledge_id]
        updated = KnowledgeUnit(
            knowledge_id=unit.knowledge_id,
            title=unit.title,
            category_id=unit.category_id,
            tags=unit.tags,
            status=status,
            created_by=unit.created_by,
            updated_by=operator_id,
            current_version_id=unit.current_version_id,
        )
        self.units[knowledge_id] = updated
        return updated


class FakePermissionRepository:
    """权限仓储内存实现。"""

    # 作用：初始化权限版本。
    def __init__(self) -> None:
        self.version = 0
        self.grants: tuple[PermissionGrant, ...] = ()

    # 作用：替换权限规则。
    async def replace_grants(self, knowledge_id, grants, operator_id):
        """保存权限集合。"""
        self.version += 1
        self.grants = grants
        return KnowledgePermissionSet(knowledge_id, grants, self.version)

    # 作用：读取权限规则。
    async def list_grants(self, knowledge_id: str) -> KnowledgePermissionSet:
        """返回权限集合。"""
        return KnowledgePermissionSet(knowledge_id, self.grants, self.version)


class FakePermissionVersion:
    """权限版本内存实现。"""

    # 作用：递增权限版本。
    async def invalidate(self, knowledge_id, affected_user_ids=()):
        """返回新版本。"""
        return 1


class FakeJobRepository:
    """任务仓储内存实现。"""

    # 作用：创建任务 ID。
    async def enqueue(self, job_type, payload, idempotency_key):
        """返回任务 ID。"""
        return str(uuid4())

    # 作用：领取任务。
    async def claim_batch(self, worker_id: str, batch_size: int) -> list[JobRecord]:
        """返回空任务列表。"""
        return []

    # 作用：标记成功。
    async def mark_succeeded(self, job_id: str) -> None:
        """空实现。"""
        return None

    # 作用：标记失败。
    async def mark_failed(self, job_id: str, error: str, retry: bool) -> None:
        """空实现。"""
        return None

    # 作用：释放超时任务。
    async def release_stale(self, timeout_seconds: int) -> int:
        """返回零。"""
        return 0


class FakeAudit:
    """审计内存实现。"""

    # 作用：接收审计事件。
    async def record(self, event_type: str, payload: dict[str, object]) -> None:
        """空实现。"""
        return None


# 作用：构造测试用知识维护工作流。
def make_workflow():
    """返回工作流和测试仓储。"""
    knowledge_repository = FakeKnowledgeRepository()
    permission_repository = FakePermissionRepository()
    workflow = KnowledgeMaintenanceWorkflow(
        repository=knowledge_repository,
        permission_repository=permission_repository,
        permission_version=FakePermissionVersion(),
        job_repository=FakeJobRepository(),
        audit=FakeAudit(),
        permission_policy=PermissionPolicy(),
    )
    return workflow, knowledge_repository, permission_repository


# 作用：验证四维权限 OR 规则。
def test_permission_policy_or_semantics() -> None:
    """验证全局、部门、角色和个人权限。"""
    policy = PermissionPolicy()
    user = UserContext(
        user_id="u1",
        department_id="dept-2",
        department_path=("dept-1", "dept-2"),
        role_ids=("role-a",),
        permission_version=1,
    )
    assert policy.matches(user, [PermissionGrant(PermissionScope.GLOBAL, "*")])
    assert policy.matches(user, [PermissionGrant(PermissionScope.DEPARTMENT, "dept-1", True)])
    assert policy.matches(user, [PermissionGrant(PermissionScope.ROLE, "role-a")])
    assert policy.matches(user, [PermissionGrant(PermissionScope.USER, "u1")])
    assert not policy.matches(user, [PermissionGrant(PermissionScope.USER, "u2")])


# 作用：验证知识创建、版本、权限和发布流程。
@pytest.mark.asyncio
async def test_knowledge_maintenance_workflow() -> None:
    """验证知识维护关键节点。"""
    workflow, repository, permission_repository = make_workflow()
    created = await workflow.ainvoke(
        {
            "command": KnowledgeMaintenanceCommand(
                action=KnowledgeAction.CREATE,
                request_id="r1",
                operator_id="admin",
                title="差旅报销标准",
                category_id="finance",
                tags=("finance",),
            )
        }
    )
    knowledge_id = created["result"].knowledge_id

    version_state = await workflow.ainvoke(
        {
            "command": KnowledgeMaintenanceCommand(
                action=KnowledgeAction.CREATE_VERSION,
                request_id="r2",
                operator_id="admin",
                knowledge_id=knowledge_id,
                source_object_key="raw/standard.pdf",
                filename="standard.pdf",
                content_type="application/pdf",
            )
        }
    )
    assert version_state["result"].job_id

    permission_state = await workflow.ainvoke(
        {
            "command": KnowledgeMaintenanceCommand(
                action=KnowledgeAction.CONFIGURE_PERMISSIONS,
                request_id="r3",
                operator_id="admin",
                knowledge_id=knowledge_id,
                grants=(PermissionGrant(PermissionScope.DEPARTMENT, "finance"),),
            )
        }
    )
    assert permission_state["result"].permission_version == 1

    with pytest.raises(ValueError):
        await workflow.ainvoke(
            {
                "command": KnowledgeMaintenanceCommand(
                    action=KnowledgeAction.PUBLISH,
                    request_id="r4",
                    operator_id="admin",
                    knowledge_id=knowledge_id,
                )
            }
        )

    version = await repository.get_current_version(knowledge_id)
    repository.versions[version.version_id] = KnowledgeVersion(
        version_id=version.version_id,
        knowledge_id=version.knowledge_id,
        version_no=version.version_no,
        source_object_key=version.source_object_key,
        markdown_object_key=version.markdown_object_key,
        filename=version.filename,
        content_type=version.content_type,
        status=VersionStatus.INDEXED,
        created_by=version.created_by,
    )
    published = await workflow.ainvoke(
        {
            "command": KnowledgeMaintenanceCommand(
                action=KnowledgeAction.PUBLISH,
                request_id="r5",
                operator_id="admin",
                knowledge_id=knowledge_id,
            )
        }
    )
    assert published["result"].status is KnowledgeStatus.PUBLISHED