"""实现最终回答输出节点。"""

import re
from typing import Any

from kb_manage_platform.common.logger import logger
from kb_manage_platform.domain.models import AnswerResult
from kb_manage_platform.domain.ports import AnswerGeneratorPort
from kb_manage_platform.engines.query_engine.base import QueryNodeBase
from kb_manage_platform.engines.query_engine.state import QaGraphState

PERMISSION_RESTRICTED_NOTICE = "部分参考资料因权限受限无法展示"
PERMISSION_RESTRICTED_WARNING = "permission_restricted_context"
_AUTHORIZATION_UNAVAILABLE_WARNING = "authorization_unavailable_default_deny"


class NodeAnswerOutput(QueryNodeBase):
    """复用 FAQ 或调用 LangChain LLM 生成最终回答。"""

    name = "node_answer_output"

    # 作用：保存回答生成端口。
    def __init__(self, generator: AnswerGeneratorPort) -> None:
        self._generator = generator

    # 作用：生成或透传最终回答，并标注权限受限情况。
    async def process(self, state: QaGraphState) -> dict[str, Any]:
        """返回最终回答。"""
        existing = state.get("faq_answer")
        if existing:
            return {"answer": existing}
        candidates = state.get("final_candidates", [])
        if not candidates:
            answer = AnswerResult(
                answer="现有知识无法支撑该问题。",
                warnings=("no_authorized_context",),
            )
            return {"answer": self._mark_permission_restriction(state, answer)}
        try:
            answer = await self._generator.generate(
                state["normalized_question"], candidates, state["request"].history
            )
        except Exception as exc:
            logger.warning("answer generation failed, using extractive fallback: %s", exc)
            answer = self._extractive_fallback(state["normalized_question"], candidates)
        return {"answer": self._mark_permission_restriction(state, answer)}

    # 作用：仅在确认存在被鉴权过滤的召回内容时添加提示。
    @classmethod
    def _mark_permission_restriction(
        cls,
        state: QaGraphState,
        answer: AnswerResult,
    ) -> AnswerResult:
        if not cls._has_permission_restricted_candidates(state):
            return answer
        text = answer.answer.rstrip()
        if PERMISSION_RESTRICTED_NOTICE not in text:
            text = f"{text}\n\n{PERMISSION_RESTRICTED_NOTICE}" if text else PERMISSION_RESTRICTED_NOTICE
        warnings = tuple(dict.fromkeys((*answer.warnings, PERMISSION_RESTRICTED_WARNING)))
        return AnswerResult(answer=text, citations=answer.citations, warnings=warnings)

    # 作用：比较鉴权前后知识单元，识别确实被过滤的召回内容。
    @staticmethod
    def _has_permission_restricted_candidates(state: QaGraphState) -> bool:
        if _AUTHORIZATION_UNAVAILABLE_WARNING in state.get("warnings", []):
            return False
        recalled = state.get("rrf_candidates", [])
        allowed_knowledge_ids = {
            candidate.knowledge_id for candidate in state.get("allowed_candidates", [])
        }
        return any(
            candidate.knowledge_id not in allowed_knowledge_ids
            for candidate in recalled
        )

    @classmethod
    def _extractive_fallback(cls, question, candidates):
        """模型不可用时，仅返回与问题最相关的已鉴权知识原文。"""
        ranked = sorted(
            (
                (cls._relevance(candidate, question), index, candidate)
                for index, candidate in enumerate(candidates)
            ),
            key=lambda item: (-item[0], item[1]),
        )
        relevant = [item for item in ranked if item[0] > 0]
        selected = tuple(
            candidate
            for _, _, candidate in (relevant or ranked)[:4]
            if candidate.content.strip()
        )
        if not selected:
            return AnswerResult(answer="现有知识无法支撑该问题。", warnings=("no_authorized_context",))
        blocks = [
            f"[S{index}] {candidate.content.strip()}"
            for index, candidate in enumerate(selected, start=1)
        ]
        return AnswerResult(
            answer="根据现有知识：\n\n" + "\n\n".join(blocks),
            citations=selected,
            warnings=("llm_unavailable_extractive_fallback",),
        )

    @staticmethod
    def _relevance(candidate, question: str) -> float:
        """使用中文字符二元组估算问题与切片的文本重合度。"""
        question_grams = NodeAnswerOutput._bigrams(question)
        candidate_text = f"{candidate.metadata.get('section_path', '')} {candidate.content}"
        candidate_grams = NodeAnswerOutput._bigrams(candidate_text)
        if not question_grams or not candidate_grams:
            return 0.0
        return len(question_grams & candidate_grams) / len(question_grams)

    @staticmethod
    def _bigrams(text: str) -> set[str]:
        normalized = re.sub(r"\W+", "", text or "")
        return {normalized[index:index + 2] for index in range(max(0, len(normalized) - 1))}