"""定义 FAQ 与知识缺口 LangGraph 状态。"""

from typing import TypedDict

from kb_manage_platform.domain.models import (
    FaqCandidate,
    FaqGapCommand,
    FaqGapResult,
    KnowledgeGap,
    QaLogRecord,
    QuestionCluster,
)


class FaqGapGraphState(TypedDict, total=False):
    """FAQ 与知识缺口工作流状态。"""

    command: FaqGapCommand
    logs: tuple[QaLogRecord, ...]
    clusters: tuple[QuestionCluster, ...]
    candidates: tuple[FaqCandidate, ...]
    gaps: tuple[KnowledgeGap, ...]
    result: FaqGapResult