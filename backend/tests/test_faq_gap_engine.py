"""验证 FAQ 语义聚类、缺口分类和 FAQ 自动发布流程。"""

import pytest

from kb_manage_platform.domain.models import (
    FaqCandidate,
    FaqCandidateStatus,
    FaqGapAction,
    FaqGapCommand,
    KnowledgeGap,
    PermissionGrant,
    QaLogRecord,
)
from kb_manage_platform.domain.services.faq_gap import (
    FaqCandidateBuilder,
    KnowledgeGapClassifier,
    SensitiveContentChecker,
)
from kb_manage_platform.engines.faq_gap_engine.main_graph import FaqGapWorkflow
from kb_manage_platform.infrastructure.adapters.faq_cluster_utils import EmbeddingQuestionClusterer


class FakeEmbedder:
    """将不同问题映射为正交向量，避免误聚类。"""

    async def embed(self, texts):
        unique = list(dict.fromkeys(texts))
        return [
            [1.0 if text == candidate else 0.0 for candidate in unique]
            for text in texts
        ]


class ParaphraseEmbedder:
    """为语义相近但文本不同的问题返回相同向量。"""

    async def embed(self, texts):
        vectors = {
            "年假有多少天": [1.0, 0.0],
            "带薪休假可以休几天": [1.0, 0.0],
            "报销多久到账": [0.0, 1.0],
        }
        return [vectors[text] for text in texts]


class FakeQaLogRepository:
    """问答日志仓储测试桩。"""

    def __init__(self, logs: tuple[QaLogRecord, ...]) -> None:
        self._logs = logs

    async def list_logs(self, window_days: int, limit: int = 5000):
        """返回固定日志。"""
        return self._logs


class FakeFaqRepository:
    """FAQ 候选仓储测试桩。"""

    def __init__(self) -> None:
        self.saved: tuple[FaqCandidate, ...] = ()
        self.published: list[str] = []

    async def save_candidates(self, candidates):
        """保存候选到内存。"""
        self.saved = tuple(candidates)

    async def get_candidate(self, candidate_id: str):
        """返回空。"""
        return None

    async def list_candidates(self, status=None):
        """返回已保存候选。"""
        return self.saved

    async def publish_candidate(
        self,
        candidate_id: str,
        grants: tuple[PermissionGrant, ...],
        operator_id: str,
    ) -> str:
        """记录发布。"""
        self.published.append(candidate_id)
        return f"faq-{candidate_id}"

    async def reject_candidate(self, candidate_id: str, operator_id: str, reason: str) -> None:
        """空实现。"""
        return None


class FakeGapRepository:
    """知识缺口仓储测试桩。"""

    async def upsert_gaps(self, gaps) -> None:
        """空实现。"""
        return None

    async def get_gap(self, gap_id: str) -> KnowledgeGap | None:
        """返回空。"""
        return None

    async def list_gaps(self, status=None):
        """返回空。"""
        return ()

    async def create_supplement_draft(
        self,
        gap_id,
        title,
        category_id,
        knowledge_id,
        operator_id,
    ) -> str:
        """返回草稿 ID。"""
        return "draft-1"

    async def resolve_by_knowledge(self, knowledge_id: str) -> int:
        """返回零。"""
        return 0

    async def set_status(self, gap_id, status, reason: str = "") -> None:
        """空实现。"""
        return None


class FakeKnowledgeRepository:
    """知识仓储测试桩。"""

    async def create_unit(self, command):
        """返回最小知识对象。"""
        raise NotImplementedError


class FakeCache:
    """FAQ 缓存测试桩。"""

    def __init__(self) -> None:
        self.invalidated: list[str] = []

    async def invalidate_question(self, question: str) -> None:
        """记录问题。"""
        self.invalidated.append(question)


class FakeAudit:
    """审计测试桩。"""

    async def record(self, event_type: str, payload: dict[str, object]) -> None:
        """空实现。"""
        return None


def make_logs() -> tuple[QaLogRecord, ...]:
    """构造 10 条相同问题日志。"""
    return tuple(
        QaLogRecord(
            request_id=f"req-{index}",
            user_id=f"user-{index % 5}",
            department_id="finance",
            question="差旅报销标准是什么",
            recall_count=2,
            authorized_count=2,
            final_count=2,
            answer_excerpt="按照公司差旅制度执行。",
            permission_signatures=("global",),
        )
        for index in range(10)
    )


@pytest.mark.asyncio
async def test_embedding_clusterer_groups_semantic_paraphrases() -> None:
    """语义相近但文本不同的问题应归入同一簇。"""
    logs = (
        QaLogRecord("r1", "u1", "d1", "年假有多少天", 1, 1, 1, "", ("global",)),
        QaLogRecord("r2", "u2", "d1", "带薪休假可以休几天", 1, 1, 1, "", ("global",)),
        QaLogRecord("r3", "u3", "d1", "报销多久到账", 1, 1, 1, "", ("global",)),
    )
    clusterer = EmbeddingQuestionClusterer(ParaphraseEmbedder())
    clusters = await clusterer.cluster(logs, threshold=0.85)
    assert [len(cluster.logs) for cluster in clusters] == [2, 1]
    assert clusters[0].similarity == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_faq_candidate_builder() -> None:
    """验证聚类和候选阈值。"""
    clusters = await EmbeddingQuestionClusterer(FakeEmbedder()).cluster(
        make_logs(), threshold=0.85
    )
    candidates = FaqCandidateBuilder().build(clusters, min_occurrences=10, min_users=5)
    assert len(candidates) == 1
    assert candidates[0].permission_signature == "global"
    assert candidates[0].status is FaqCandidateStatus.CANDIDATE


@pytest.mark.asyncio
async def test_gap_classifier_excludes_permission_blocked() -> None:
    """验证缺口分类规则。"""
    logs = (
        QaLogRecord("r1", "u1", "d1", "缺失问题", 0, 0, 0, "", ()),
        QaLogRecord("r2", "u2", "d1", "受限问题", 3, 0, 0, "", ("department:hr",)),
        QaLogRecord("r3", "u3", "d1", "低置信问题", 3, 2, 0, "", ("global",)),
    )
    gaps = await KnowledgeGapClassifier().classify(
        logs,
        EmbeddingQuestionClusterer(FakeEmbedder()),
        threshold=0.85,
    )
    assert {gap.gap_type.value for gap in gaps} == {"no_candidate", "low_confidence"}


@pytest.mark.asyncio
async def test_mine_faq_workflow() -> None:
    """验证 FAQ 挖掘与自动发布。"""
    faq_repository = FakeFaqRepository()
    cache = FakeCache()
    workflow = FaqGapWorkflow(
        qa_log_repository=FakeQaLogRepository(make_logs()),
        faq_repository=faq_repository,
        gap_repository=FakeGapRepository(),
        knowledge_repository=FakeKnowledgeRepository(),
        cache=cache,
        audit=FakeAudit(),
        sensitive_checker=SensitiveContentChecker(),
        question_clusterer=EmbeddingQuestionClusterer(FakeEmbedder()),
    )
    state = await workflow.ainvoke(
        {
            "command": FaqGapCommand(
                action=FaqGapAction.MINE_FAQ,
                request_id="r1",
                operator_id="admin",
                min_occurrences=10,
                min_users=5,
            )
        }
    )
    assert state["result"].processed_count == 1
    assert faq_repository.published
    assert cache.invalidated