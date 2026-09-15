"""识别并保存知识缺口。"""

from typing import Any

from kb_manage_platform.domain.ports import KnowledgeGapRepositoryPort, QuestionClustererPort
from kb_manage_platform.domain.services.faq_gap import KnowledgeGapClassifier
from kb_manage_platform.engines.faq_gap_engine.base import FaqGapNodeBase
from kb_manage_platform.engines.faq_gap_engine.state import FaqGapGraphState


class NodeDetectGaps(FaqGapNodeBase):
    """识别无候选和低置信度问题。"""

    name = "node_detect_gaps"

    # 作用：保存缺口仓储、语义聚类器和分类器。
    def __init__(
        self,
        repository: KnowledgeGapRepositoryPort,
        clusterer: QuestionClustererPort,
        classifier: KnowledgeGapClassifier,
    ) -> None:
        self._repository = repository
        self._clusterer = clusterer
        self._classifier = classifier

    # 作用：识别并写入知识缺口。
    async def process(self, state: FaqGapGraphState) -> dict[str, Any]:
        """返回缺口集合。"""
        command = state["command"]
        gaps = await self._classifier.classify(
            state.get("logs", ()), self._clusterer, command.similarity_threshold
        )
        await self._repository.upsert_gaps(gaps)
        return {"gaps": gaps}