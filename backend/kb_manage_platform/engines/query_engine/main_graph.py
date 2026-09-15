"""装配知识库问答 LangGraph。"""

from typing import Any

from langgraph.graph import END, StateGraph

from kb_manage_platform.domain.models import RetrievalPolicy
from kb_manage_platform.domain.ports import (
    AnswerGeneratorPort,
    AuditPort,
    AuthorizationPort,
    FaqCachePort,
    HybridRetrieverPort,
    HydeGeneratorPort,
    RerankerPort,
    VectorRetrieverPort,
)
from kb_manage_platform.domain.services.rrf import RrfFuser
from kb_manage_platform.engines.query_engine.nodes.node_answer_output import NodeAnswerOutput
from kb_manage_platform.engines.query_engine.nodes.node_audit import NodeAudit
from kb_manage_platform.engines.query_engine.nodes.node_auth_filter import NodeAuthFilter
from kb_manage_platform.engines.query_engine.nodes.node_faq_cache import NodeFaqCache
from kb_manage_platform.engines.query_engine.nodes.node_query_entry import NodeQueryEntry
from kb_manage_platform.engines.query_engine.nodes.node_rerank import NodeRerank
from kb_manage_platform.engines.query_engine.nodes.node_rrf import NodeRrf
from kb_manage_platform.engines.query_engine.nodes.node_search_embedding import NodeSearchEmbedding
from kb_manage_platform.engines.query_engine.nodes.node_search_hyde import NodeSearchHyde
from kb_manage_platform.engines.query_engine.state import QaGraphState


class KBQueryWorkflow:
    """知识库问答工作流，负责节点创建、注册和路由。"""

    # 作用：保存问答依赖并初始化 LangGraph。
    def __init__(
        self,
        faq_cache: FaqCachePort,
        hybrid_retriever: HybridRetrieverPort,
        hyde_generator: HydeGeneratorPort,
        vector_retriever: VectorRetrieverPort,
        reranker: RerankerPort,
        authorizer: AuthorizationPort,
        answer_generator: AnswerGeneratorPort,
        audit: AuditPort,
        policy: RetrievalPolicy,
        hyde_count: int,
        rrf_fuser: RrfFuser,
    ) -> None:
        self._workflow = StateGraph(QaGraphState)
        self._compiled_app: Any = None
        self._init_nodes(
            faq_cache,
            hybrid_retriever,
            hyde_generator,
            vector_retriever,
            reranker,
            authorizer,
            answer_generator,
            audit,
            policy,
            hyde_count,
            rrf_fuser,
        )
        self._register_nodes()
        self._setup_routes()

    # 作用：创建问答流程的节点实例。
    def _init_nodes(
        self,
        faq_cache: FaqCachePort,
        hybrid_retriever: HybridRetrieverPort,
        hyde_generator: HydeGeneratorPort,
        vector_retriever: VectorRetrieverPort,
        reranker: RerankerPort,
        authorizer: AuthorizationPort,
        answer_generator: AnswerGeneratorPort,
        audit: AuditPort,
        policy: RetrievalPolicy,
        hyde_count: int,
        rrf_fuser: RrfFuser,
    ) -> None:
        """初始化节点对象。"""
        self.node_entry = NodeQueryEntry()
        self.node_faq_cache = NodeFaqCache(faq_cache)
        self.node_search_embedding = NodeSearchEmbedding(hybrid_retriever, policy.hybrid_top_k)
        self.node_search_hyde = NodeSearchHyde(
            hyde_generator,
            vector_retriever,
            hyde_count=max(1, hyde_count),
            top_k=policy.hyde_top_k,
        )
        self.node_rrf = NodeRrf(rrf_fuser, policy.rrf_top_k)
        self.node_auth_pre = NodeAuthFilter(authorizer, "rrf_candidates", "allowed_candidates")
        self.node_rerank = NodeRerank(reranker, policy.reranker_top_k)
        self.node_auth_final = NodeAuthFilter(authorizer, "reranked_candidates", "final_candidates")
        self.node_answer_output = NodeAnswerOutput(answer_generator)
        self.node_audit = NodeAudit(audit)

    # 作用：将节点注册到 LangGraph。
    def _register_nodes(self) -> None:
        """注册全部节点。"""
        self._workflow.add_node("node_entry", self.node_entry)
        self._workflow.add_node("node_faq_cache", self.node_faq_cache)
        self._workflow.add_node("node_search_embedding", self.node_search_embedding)
        self._workflow.add_node("node_search_hyde", self.node_search_hyde)
        self._workflow.add_node("node_rrf", self.node_rrf)
        self._workflow.add_node("node_auth_pre", self.node_auth_pre)
        self._workflow.add_node("node_rerank", self.node_rerank)
        self._workflow.add_node("node_auth_final", self.node_auth_final)
        self._workflow.add_node("node_answer_output", self.node_answer_output)
        self._workflow.add_node("node_audit", self.node_audit)

    # 作用：根据 FAQ 命中情况决定后续节点。
    def _route_after_faq(self, state: QaGraphState) -> str | list[str]:
        """FAQ 命中时直答，否则并行启动两路检索。"""
        if state.get("faq_answer"):
            return "node_answer_output"
        return ["node_search_embedding", "node_search_hyde"]

    # 作用：设置图入口、条件边和普通边。
    def _setup_routes(self) -> None:
        """配置问答流程路由。"""
        self._workflow.set_entry_point("node_entry")
        self._workflow.add_edge("node_entry", "node_faq_cache")
        self._workflow.add_conditional_edges(
            "node_faq_cache",
            self._route_after_faq,
            {
                "node_answer_output": "node_answer_output",
                "node_search_embedding": "node_search_embedding",
                "node_search_hyde": "node_search_hyde",
            },
        )
        self._workflow.add_edge("node_search_embedding", "node_rrf")
        self._workflow.add_edge("node_search_hyde", "node_rrf")
        self._workflow.add_edge("node_rrf", "node_auth_pre")
        self._workflow.add_edge("node_auth_pre", "node_rerank")
        self._workflow.add_edge("node_rerank", "node_auth_final")
        self._workflow.add_edge("node_auth_final", "node_answer_output")
        self._workflow.add_edge("node_answer_output", "node_audit")
        self._workflow.add_edge("node_audit", END)

    # 作用：懒加载编译 LangGraph。
    def compile(self) -> Any:
        """编译并返回工作流。"""
        if self._compiled_app is None:
            self._compiled_app = self._workflow.compile()
        return self._compiled_app

    # 作用：执行问答工作流。
    async def ainvoke(self, initial_state: QaGraphState) -> QaGraphState:
        """异步执行问答图。"""
        return await self.compile().ainvoke(initial_state)