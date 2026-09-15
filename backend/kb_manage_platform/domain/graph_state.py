"""定义 LangGraph 问答与入库流程的显式状态结构。"""

import operator
from typing import Annotated, TypedDict

from kb_manage_platform.domain.models import (
    AnswerResult,
    ImageSummary,
    IngestionRequest,
    KnowledgeChunk,
    QuestionRequest,
    RetrievedCandidate,
)


class QaGraphState(TypedDict, total=False):
    """AI 鉴权问答图状态。"""

    request: QuestionRequest
    normalized_question: str
    faq_answer: AnswerResult
    original_candidates: Annotated[list[RetrievedCandidate], operator.add]
    hyde_candidates: Annotated[list[RetrievedCandidate], operator.add]
    rrf_candidates: list[RetrievedCandidate]
    allowed_candidates: list[RetrievedCandidate]
    reranked_candidates: list[RetrievedCandidate]
    final_candidates: list[RetrievedCandidate]
    answer: AnswerResult
    warnings: Annotated[list[str], operator.add]


class IngestionGraphState(TypedDict, total=False):
    """知识入库与图片摘要图状态。"""

    request: IngestionRequest
    markdown: str
    image_keys: list[str]
    image_summaries: list[ImageSummary]
    chunks: list[KnowledgeChunk]
    vectors: list[list[float]]
    vector_ids: list[str]
    indexed: bool
    published: bool