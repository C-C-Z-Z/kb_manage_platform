"""实现 FAQ 候选判定和知识缺口分类规则。"""

from collections.abc import Sequence
from uuid import uuid4

from kb_manage_platform.domain.models import (
    FaqCandidate,
    FaqCandidateStatus,
    KnowledgeGap,
    KnowledgeGapStatus,
    KnowledgeGapType,
    QaLogRecord,
    QuestionCluster,
)
from kb_manage_platform.domain.ports import QuestionClustererPort


class FaqCandidateBuilder:
    """根据问题簇生成 FAQ 候选。"""

    # 作用：过滤低频簇并构造 FAQ 候选。
    def build(
        self,
        clusters: Sequence[QuestionCluster],
        min_occurrences: int,
        min_users: int,
    ) -> tuple[FaqCandidate, ...]:
        """返回满足阈值的候选。"""
        candidates: list[FaqCandidate] = []
        for cluster in clusters:
            users = {item.user_id for item in cluster.logs}
            if len(cluster.logs) < min_occurrences or len(users) < min_users:
                continue
            signatures = [
                signature
                for item in cluster.logs
                for signature in item.permission_signatures
            ]
            if not signatures:
                signature = "unknown"
            elif all(value == "global" for value in signatures):
                signature = "global"
            elif len(set(signatures)) == 1:
                signature = signatures[0]
            else:
                signature = "mixed"
            status = (
                FaqCandidateStatus.CANDIDATE
                if signature == "global"
                else FaqCandidateStatus.PENDING_REVIEW
            )
            candidates.append(
                FaqCandidate(
                    candidate_id=str(uuid4()),
                    representative_question=cluster.representative_question,
                    standard_answer=max(
                        cluster.logs,
                        key=lambda item: len(item.answer_excerpt),
                    ).answer_excerpt,
                    frequency=len(cluster.logs),
                    distinct_users=len(users),
                    permission_signature=signature,
                    status=status,
                    confidence=cluster.similarity,
                    source_request_ids=tuple(item.request_id for item in cluster.logs),
                )
            )
        return tuple(candidates)


class KnowledgeGapClassifier:
    """根据问答审计识别真实缺口和低置信度缺口。"""

    # 作用：将问答日志转换为聚合后的知识缺口。
    async def classify(
        self,
        logs: Sequence[QaLogRecord],
        clusterer: QuestionClustererPort,
        threshold: float,
    ) -> tuple[KnowledgeGap, ...]:
        """返回知识缺口。"""
        gap_logs = [
            log
            for log in logs
            if log.recall_count == 0
            or (log.authorized_count > 0 and log.final_count == 0)
        ]
        clusters = await clusterer.cluster(gap_logs, threshold)
        gaps: list[KnowledgeGap] = []
        for cluster in clusters:
            no_candidate = any(item.recall_count == 0 for item in cluster.logs)
            gap_type = (
                KnowledgeGapType.NO_CANDIDATE
                if no_candidate
                else KnowledgeGapType.LOW_CONFIDENCE
            )
            gaps.append(
                KnowledgeGap(
                    gap_id=str(uuid4()),
                    representative_question=cluster.representative_question,
                    gap_type=gap_type,
                    status=KnowledgeGapStatus.PENDING,
                    frequency=len(cluster.logs),
                    department_ids=tuple(sorted({item.department_id for item in cluster.logs})),
                    max_similarity=cluster.similarity,
                    suggested_category="pending",
                    source_request_ids=tuple(item.request_id for item in cluster.logs),
                )
            )
        return tuple(gaps)


class SensitiveContentChecker:
    """使用可配置关键词执行最小敏感内容检测。"""

    # 作用：保存敏感关键词。
    def __init__(self, keywords: tuple[str, ...] = ()) -> None:
        self._keywords = tuple(keyword.casefold() for keyword in keywords if keyword.strip())

    # 作用：判断文本是否通过敏感内容检查。
    def is_safe(self, text: str) -> bool:
        """返回是否可进入自动发布。"""
        normalized = text.casefold()
        return all(keyword not in normalized for keyword in self._keywords)