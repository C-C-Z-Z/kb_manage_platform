"""验证阶段 A 新增领域状态和服务编排行为。"""

import pytest

from kb_manage_platform.domain.models import (
    AnswerResult,
    JobRecord,
    JobStage,
    KnowledgePermissionSet,
    KnowledgeStatus,
    KnowledgeUnit,
    PermissionGrant,
    PermissionScope,
    UserContext,
)
from kb_manage_platform.domain.services.permissions import PermissionPolicy
from kb_manage_platform.services.query_service import QueryService


class TrustedIdentityRepository:
    """若被调用则测试失败。"""

    async def get_user_context(self, user_id: str) -> UserContext:
        """返回不可达状态。"""
        raise AssertionError("trusted context should bypass identity lookup")


class ConversationRepository:
    """记录会话写入。"""

    def __init__(self) -> None:
        self.saved = False

    async def get_recent_messages(self, session_id: str, user_id: str, limit: int):
        """返回空历史。"""
        return ()

    async def save_turn(self, request_id, session_id, user_id, question, answer) -> None:
        """记录回答写入。"""
        self.saved = True


class QueryWorkflow:
    """返回固定回答。"""

    async def ainvoke(self, state):
        """校验可信用户上下文。"""
        assert state["request"].user.user_id == "user-trusted"
        return {"answer": AnswerResult(answer="受控回答")}


class AuditLogger:
    """记录指标事件。"""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    async def record(self, event_type: str, payload: dict[str, object]) -> None:
        """保存审计事件。"""
        self.events.append((event_type, payload))


@pytest.mark.asyncio
async def test_query_service_uses_trusted_context_and_records_metrics() -> None:
    """验证路由传入的用户上下文不会被客户端身份覆盖。"""
    conversation = ConversationRepository()
    audit = AuditLogger()
    service = QueryService(QueryWorkflow(), TrustedIdentityRepository(), conversation, audit)
    user = UserContext(
        user_id="user-trusted",
        department_id="dept-product",
        role_ids=("role-user",),
        permission_version=1,
    )
    _, answer = await service.ask("差旅标准是什么？", "session-trusted", user)
    assert answer.answer == "受控回答"
    assert conversation.saved is True
    assert audit.events[0][0] == "qa.metrics"
    assert audit.events[0][1]["estimated_tokens"] > 0


def test_job_record_has_phase_progress_defaults() -> None:
    """验证任务默认阶段和进度稳定。"""
    job = JobRecord(job_id="job-1", job_type="ingest_document", payload={})
    assert job.progress == 0
    assert job.stage is JobStage.QUEUED
    assert job.last_error == ""


def test_permission_policy_default_deny_and_global_allow() -> None:
    """验证空权限拒绝、全局权限放行。"""
    policy = PermissionPolicy()
    user = UserContext(
        user_id="user-1",
        department_id="dept-product",
        role_ids=("role-user",),
        permission_version=1,
    )
    assert policy.matches(user, ()) is False
    assert policy.matches(
        user,
        (PermissionGrant(scope=PermissionScope.GLOBAL, subject_id=""),),
    ) is True

class KnowledgeRepository:
    """内存知识仓储。"""

    async def list_units(self, query, status, category_id, page, page_size):
        """返回两个知识单元。"""
        units = (
            KnowledgeUnit("knowledge-1", "可访问", "cat", (), KnowledgeStatus.DRAFT, "user-1", "user-1"),
            KnowledgeUnit("knowledge-2", "不可访问", "cat", (), KnowledgeStatus.DRAFT, "user-2", "user-2"),
        )
        return units, len(units)

    async def get_unit(self, knowledge_id: str):
        """返回指定知识。"""
        return (await self.list_units("", None, "", 1, 10))[0][0 if knowledge_id == "knowledge-1" else 1]


class PermissionRepository:
    """内存权限仓储。"""

    async def list_grants(self, knowledge_id: str) -> KnowledgePermissionSet:
        """仅 knowledge-1 对 user-1 授权。"""
        grants = (
            (PermissionGrant(PermissionScope.USER, "user-1"),)
            if knowledge_id == "knowledge-1"
            else ()
        )
        return KnowledgePermissionSet(knowledge_id, grants, 1 if grants else 0)

    async def list_grants_batch(self, knowledge_ids):
        """批量返回权限集。"""
        return {knowledge_id: await self.list_grants(knowledge_id) for knowledge_id in knowledge_ids}


class GapRepository:
    """知识缺口占位实现。"""

    async def resolve_by_knowledge(self, knowledge_id: str) -> int:
        """返回零。"""
        return 0


class ObjectStorage:
    """对象存储占位实现。"""

    async def put_bytes(self, bucket, object_key, content, content_type):
        """返回对象键。"""
        return object_key


class KnowledgeWorkflow:
    """知识维护占位实现。"""

    async def ainvoke(self, state):
        """返回空状态。"""
        return state


@pytest.mark.asyncio
async def test_knowledge_list_and_detail_apply_data_permissions() -> None:
    """验证知识元数据读取按四维权限过滤。"""
    from kb_manage_platform.services.knowledge_service import KnowledgeService

    service = KnowledgeService(
        KnowledgeWorkflow(),
        GapRepository(),
        KnowledgeRepository(),
        PermissionRepository(),
        ObjectStorage(),
        "raw",
        PermissionPolicy(),
    )
    user = UserContext(
        user_id="user-1",
        department_id="dept-product",
        role_ids=("role-user",),
        permission_version=1,
    )
    units, total = await service.list_units(user, "", None, "", 1, 20)
    assert total == 1
    assert units[0].knowledge_id == "knowledge-1"
    with pytest.raises(PermissionError):
        await service.get_unit("knowledge-2", user)


