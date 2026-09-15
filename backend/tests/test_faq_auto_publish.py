"""验证全局安全 FAQ 可以自动发布，受限或敏感内容必须审核。"""

import pytest

from kb_manage_platform.domain.models import (
    FaqCandidateStatus,
    FaqGapAction,
    FaqGapCommand,
    QaLogRecord,
)
from kb_manage_platform.domain.services.faq_gap import (
    FaqCandidateBuilder,
    SensitiveContentChecker,
)
from kb_manage_platform.engines.faq_gap_engine.nodes.node_mine_faq import NodeMineFaq
from kb_manage_platform.infrastructure.adapters.faq_cluster_utils import EmbeddingQuestionClusterer
from kb_manage_platform.infrastructure.mysql.qa_log_repository import MysqlQaLogRepository


class FakeEmbedder:
    """返回固定语义向量的测试桩。"""

    async def embed(self, texts):
        """所有测试问题使用同一向量。"""
        return [[1.0, 0.0] for _ in texts]


class FakeFaqRepository:
    def __init__(self) -> None:
        self.saved = ()
        self.published: list[str] = []

    async def save_candidates(self, candidates) -> None:
        self.saved = tuple(candidates)

    async def publish_candidate(self, candidate_id, grants, operator_id) -> str:
        self.published.append(candidate_id)
        return f"faq-{candidate_id}"


class FakeCache:
    def __init__(self) -> None:
        self.invalidated: list[str] = []

    async def invalidate_question(self, question: str) -> None:
        self.invalidated.append(question)


def make_logs(answer: str = "按照公司差旅制度执行。") -> tuple[QaLogRecord, ...]:
    return tuple(
        QaLogRecord(
            request_id=f"req-{index}",
            user_id=f"user-{index % 5}",
            department_id="finance",
            question="差旅报销标准是什么？",
            recall_count=2,
            authorized_count=2,
            final_count=2,
            answer_excerpt=answer,
            permission_signatures=("global",),
            authorized_knowledge_ids=("knowledge-travel",),
        )
        for index in range(10)
    )


@pytest.mark.asyncio
async def test_candidate_without_permission_signature_requires_review() -> None:
    logs = tuple(
        QaLogRecord(
            request_id=f"req-{index}",
            user_id=f"user-{index % 5}",
            department_id="finance",
            question="差旅报销标准是什么？",
            recall_count=2,
            authorized_count=2,
            final_count=2,
            answer_excerpt="按照公司差旅制度执行。",
            permission_signatures=(),
            authorized_knowledge_ids=("knowledge-travel",),
        )
        for index in range(10)
    )
    clusters = await EmbeddingQuestionClusterer(FakeEmbedder()).cluster(
        logs, threshold=0.85
    )
    candidates = FaqCandidateBuilder().build(clusters, 10, 5)
    assert candidates[0].permission_signature == "unknown"
    assert candidates[0].status is FaqCandidateStatus.PENDING_REVIEW


def test_qa_log_repository_recomputes_global_signature() -> None:
    record = MysqlQaLogRepository._to_record(
        {
            "request_id": "req-1",
            "user_id": "user-1",
            "question": "差旅报销标准是什么？",
            "recall_count": 2,
            "authorized_count": 1,
            "final_count": 1,
            "answer_excerpt": "按照公司差旅制度执行。",
            "permission_signatures": [],
            "authorized_knowledge_ids": ["knowledge-travel"],
        },
        {"knowledge-travel": "global"},
    )
    assert record.permission_signatures == ("global",)


@pytest.mark.asyncio
async def test_safe_global_candidate_is_auto_published() -> None:
    repository = FakeFaqRepository()
    cache = FakeCache()
    node = NodeMineFaq(
        repository=repository,
        clusterer=EmbeddingQuestionClusterer(FakeEmbedder()),
        builder=FaqCandidateBuilder(),
        cache=cache,
        sensitive_checker=SensitiveContentChecker(("密码",)),
    )
    state = {
        "command": FaqGapCommand(
            action=FaqGapAction.MINE_FAQ,
            request_id="r1",
            operator_id="admin",
            min_occurrences=10,
            min_users=5,
        ),
        "logs": make_logs(),
    }
    result = await node.process(state)
    assert result["candidates"][0].status is FaqCandidateStatus.CANDIDATE
    assert repository.published


@pytest.mark.asyncio
async def test_sensitive_global_candidate_requires_review() -> None:
    repository = FakeFaqRepository()
    cache = FakeCache()
    node = NodeMineFaq(
        repository=repository,
        clusterer=EmbeddingQuestionClusterer(FakeEmbedder()),
        builder=FaqCandidateBuilder(),
        cache=cache,
        sensitive_checker=SensitiveContentChecker(("密码",)),
    )
    state = {
        "command": FaqGapCommand(
            action=FaqGapAction.MINE_FAQ,
            request_id="r1",
            operator_id="admin",
            min_occurrences=10,
            min_users=5,
        ),
        "logs": make_logs("系统密码需要定期更换。"),
    }
    result = await node.process(state)
    assert result["candidates"][0].status is FaqCandidateStatus.PENDING_REVIEW
    assert repository.published == []