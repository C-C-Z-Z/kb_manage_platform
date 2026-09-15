"""实现 Reranker 精排节点。"""

import re
from typing import Any

from kb_manage_platform.domain.ports import RerankerPort
from kb_manage_platform.engines.query_engine.base import QueryNodeBase
from kb_manage_platform.engines.query_engine.state import QaGraphState


class NodeRerank(QueryNodeBase):
    """对授权候选执行精排。"""

    name = "node_rerank"

    # 作用：保存 Reranker 端口和 Top K。
    def __init__(self, reranker: RerankerPort, top_k: int) -> None:
        self._reranker = reranker
        self._top_k = top_k

    # 作用：重排 allowed_candidates。
    async def process(self, state: QaGraphState) -> dict[str, Any]:
        """返回重排候选。"""
        candidates = list(state.get("allowed_candidates", []))
        try:
            candidates = list(await self._reranker.rerank(state["normalized_question"], candidates, self._top_k))
        except Exception:
            return {
                "reranked_candidates": self._lexical_fallback(
                    state["normalized_question"], candidates, self._top_k
                ),
                "warnings": ["reranker_unavailable_lexical_fallback"],
            }
        return {"reranked_candidates": candidates}

    @staticmethod
    def _lexical_fallback(question: str, candidates, top_k: int):
        """重排服务不可用时，按问题与章节/正文的中文二元组重合度排序。"""
        question_grams = NodeRerank._bigrams(question)
        ranked = []
        for index, candidate in enumerate(candidates):
            text = f"{candidate.metadata.get('section_path', '')} {candidate.content}"
            grams = NodeRerank._bigrams(text)
            overlap = len(question_grams & grams) / len(question_grams) if question_grams else 0.0
            ranked.append((overlap, candidate.score, -index, candidate))
        ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [item[3] for item in ranked[: max(1, top_k)]]

    @staticmethod
    def _bigrams(text: str) -> set[str]:
        normalized = re.sub(r"\W+", "", text or "")
        return {normalized[index:index + 2] for index in range(max(0, len(normalized) - 1))}