"""装配 FAQ 与知识缺口闭环 LangGraph。"""

from typing import Any

from langgraph.graph import END, StateGraph

from kb_manage_platform.domain.models import FaqGapAction
from kb_manage_platform.domain.ports import (
    AuditPort,
    FaqCacheInvalidationPort,
    FaqManagementRepositoryPort,
    KnowledgeGapRepositoryPort,
    KnowledgeRepositoryPort,
    QaLogRepositoryPort,
    QuestionClustererPort,
)
from kb_manage_platform.domain.services.faq_gap import (
    FaqCandidateBuilder,
    KnowledgeGapClassifier,
    SensitiveContentChecker,
)
from kb_manage_platform.engines.faq_gap_engine.nodes.node_audit import NodeFaqGapAudit
from kb_manage_platform.engines.faq_gap_engine.nodes.node_convert_gap import NodeConvertGap
from kb_manage_platform.engines.faq_gap_engine.nodes.node_detect_gaps import NodeDetectGaps
from kb_manage_platform.engines.faq_gap_engine.nodes.node_entry import NodeFaqGapEntry
from kb_manage_platform.engines.faq_gap_engine.nodes.node_load_logs import NodeLoadQaLogs
from kb_manage_platform.engines.faq_gap_engine.nodes.node_mine_faq import NodeMineFaq
from kb_manage_platform.engines.faq_gap_engine.nodes.node_resolve_gap import NodeResolveGap
from kb_manage_platform.engines.faq_gap_engine.nodes.node_review_faq import NodeReviewFaq
from kb_manage_platform.engines.faq_gap_engine.state import FaqGapGraphState


class FaqGapWorkflow:
    """FAQ 沉淀和知识缺口闭环工作流。"""

    # 作用：保存依赖并初始化工作流。
    def __init__(
        self,
        qa_log_repository: QaLogRepositoryPort,
        faq_repository: FaqManagementRepositoryPort,
        gap_repository: KnowledgeGapRepositoryPort,
        knowledge_repository: KnowledgeRepositoryPort,
        cache: FaqCacheInvalidationPort,
        audit: AuditPort,
        sensitive_checker: SensitiveContentChecker,
        question_clusterer: QuestionClustererPort,
    ) -> None:
        self._workflow = StateGraph(FaqGapGraphState)
        self._compiled_app: Any = None
        self._init_nodes(
            qa_log_repository,
            faq_repository,
            gap_repository,
            knowledge_repository,
            cache,
            audit,
            sensitive_checker,
            question_clusterer,
        )
        self._register_nodes()
        self._setup_routes()

    # 作用：初始化 FAQ 和缺口节点。
    def _init_nodes(
        self,
        qa_log_repository: QaLogRepositoryPort,
        faq_repository: FaqManagementRepositoryPort,
        gap_repository: KnowledgeGapRepositoryPort,
        knowledge_repository: KnowledgeRepositoryPort,
        cache: FaqCacheInvalidationPort,
        audit: AuditPort,
        sensitive_checker: SensitiveContentChecker,
        question_clusterer: QuestionClustererPort,
    ) -> None:
        """创建节点对象。"""
        self.node_entry = NodeFaqGapEntry()
        self.node_load_logs = NodeLoadQaLogs(qa_log_repository)
        self.node_mine_faq = NodeMineFaq(
            faq_repository,
            question_clusterer,
            FaqCandidateBuilder(),
            cache,
            sensitive_checker,
        )
        self.node_detect_gaps = NodeDetectGaps(
            gap_repository, question_clusterer, KnowledgeGapClassifier()
        )
        self.node_review_faq = NodeReviewFaq(faq_repository, cache)
        self.node_convert_gap = NodeConvertGap(knowledge_repository, gap_repository)
        self.node_resolve_gap = NodeResolveGap(gap_repository)
        self.node_audit = NodeFaqGapAudit(audit)

    # 作用：注册工作流节点。
    def _register_nodes(self) -> None:
        """注册节点到 LangGraph。"""
        self._workflow.add_node("node_entry", self.node_entry)
        self._workflow.add_node("node_load_logs", self.node_load_logs)
        self._workflow.add_node("node_mine_faq", self.node_mine_faq)
        self._workflow.add_node("node_detect_gaps", self.node_detect_gaps)
        self._workflow.add_node("node_review_faq", self.node_review_faq)
        self._workflow.add_node("node_convert_gap", self.node_convert_gap)
        self._workflow.add_node("node_resolve_gap", self.node_resolve_gap)
        self._workflow.add_node("node_audit", self.node_audit)

    # 作用：根据动作选择后续节点。
    def _route_after_entry(self, state: FaqGapGraphState) -> str:
        """返回动作对应节点。"""
        return {
            FaqGapAction.MINE_FAQ: "node_load_logs",
            FaqGapAction.DETECT_GAPS: "node_load_logs",
            FaqGapAction.REVIEW_FAQ: "node_review_faq",
            FaqGapAction.CONVERT_GAP: "node_convert_gap",
            FaqGapAction.RESOLVE_GAP: "node_resolve_gap",
        }[state["command"].action]

    # 作用：根据动作选择日志分析节点。
    def _route_after_logs(self, state: FaqGapGraphState) -> str:
        """返回 FAQ 或缺口分析节点。"""
        if state["command"].action is FaqGapAction.MINE_FAQ:
            return "node_mine_faq"
        return "node_detect_gaps"

    # 作用：设置工作流路由。
    def _setup_routes(self) -> None:
        """配置 FAQ 与缺口流程边。"""
        self._workflow.set_entry_point("node_entry")
        self._workflow.add_conditional_edges(
            "node_entry",
            self._route_after_entry,
            {
                "node_load_logs": "node_load_logs",
                "node_review_faq": "node_review_faq",
                "node_convert_gap": "node_convert_gap",
                "node_resolve_gap": "node_resolve_gap",
            },
        )
        self._workflow.add_conditional_edges(
            "node_load_logs",
            self._route_after_logs,
            {"node_mine_faq": "node_mine_faq", "node_detect_gaps": "node_detect_gaps"},
        )
        for node_name in (
            "node_mine_faq",
            "node_detect_gaps",
            "node_review_faq",
            "node_convert_gap",
            "node_resolve_gap",
        ):
            self._workflow.add_edge(node_name, "node_audit")
        self._workflow.add_edge("node_audit", END)

    # 作用：懒加载编译工作流。
    def compile(self) -> Any:
        """编译并返回工作流。"""
        if self._compiled_app is None:
            self._compiled_app = self._workflow.compile()
        return self._compiled_app

    # 作用：执行 FAQ 或知识缺口工作流。
    async def ainvoke(self, initial_state: FaqGapGraphState) -> FaqGapGraphState:
        """返回工作流最终状态。"""
        return await self.compile().ainvoke(initial_state)