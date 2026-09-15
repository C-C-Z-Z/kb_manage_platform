"""挖掘 FAQ 候选并按权限签名处理。"""

from dataclasses import replace
from typing import Any

from kb_manage_platform.domain.models import FaqCandidateStatus, PermissionGrant, PermissionScope
from kb_manage_platform.domain.ports import (
    FaqCacheInvalidationPort,
    FaqManagementRepositoryPort,
    QuestionClustererPort,
)
from kb_manage_platform.domain.services.faq_gap import FaqCandidateBuilder, SensitiveContentChecker
from kb_manage_platform.engines.faq_gap_engine.base import FaqGapNodeBase
from kb_manage_platform.engines.faq_gap_engine.state import FaqGapGraphState


class NodeMineFaq(FaqGapNodeBase):
    """执行问题聚类、候选生成和安全自动发布。"""

    name = "node_mine_faq"

    # 作用：保存 FAQ 仓储、聚类器、候选构建器和缓存失效端口。
    def __init__(
        self,
        repository: FaqManagementRepositoryPort,
        clusterer: QuestionClustererPort,
        builder: FaqCandidateBuilder,
        cache: FaqCacheInvalidationPort,
        sensitive_checker: SensitiveContentChecker,
    ) -> None:
        self._repository = repository
        self._clusterer = clusterer
        self._builder = builder
        self._cache = cache
        self._sensitive_checker = sensitive_checker

    # 作用：生成并保存候选，全局候选自动发布。
    async def process(self, state: FaqGapGraphState) -> dict[str, Any]:
        """返回候选集合。"""
        command = state["command"]
        clusters = await self._clusterer.cluster(
            state.get("logs", ()), command.similarity_threshold
        )
        generated = self._builder.build(clusters, command.min_occurrences, command.min_users)
        candidates = tuple(
            replace(candidate, status=FaqCandidateStatus.PENDING_REVIEW)
            if candidate.status is FaqCandidateStatus.CANDIDATE
            and (
                not self._sensitive_checker.is_safe(candidate.representative_question)
                or not self._sensitive_checker.is_safe(candidate.standard_answer)
            )
            else candidate
            for candidate in generated
        )
        await self._repository.save_candidates(candidates)
        for candidate in candidates:
            if candidate.status is FaqCandidateStatus.CANDIDATE:
                await self._repository.publish_candidate(
                    candidate.candidate_id,
                    (PermissionGrant(PermissionScope.GLOBAL, "*"),),
                    command.operator_id,
                )
                await self._cache.invalidate_question(candidate.representative_question)
        return {"clusters": clusters, "candidates": candidates}