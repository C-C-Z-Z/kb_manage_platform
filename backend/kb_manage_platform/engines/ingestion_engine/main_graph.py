"""装配知识库文档入库 LangGraph。"""

from typing import Any

from langgraph.graph import END, StateGraph

from kb_manage_platform.domain.ports import (
    AuditPort,
    ChunkerPort,
    DocumentParserPort,
    DocumentRepositoryPort,
    EmbedderPort,
    ImageSummarizerPort,
    VectorIndexPort,
)
from kb_manage_platform.engines.ingestion_engine.nodes.node_audit import NodeImportAudit
from kb_manage_platform.engines.ingestion_engine.nodes.node_document_split import NodeDocumentSplit
from kb_manage_platform.engines.ingestion_engine.nodes.node_embedding import NodeEmbedding
from kb_manage_platform.engines.ingestion_engine.nodes.node_entry import NodeEntry
from kb_manage_platform.engines.ingestion_engine.nodes.node_milvus_import import MilvusImportNode
from kb_manage_platform.engines.ingestion_engine.nodes.node_mineru_parse import NodeMineruParse
from kb_manage_platform.engines.ingestion_engine.nodes.node_publish import NodeIndexVersion
from kb_manage_platform.engines.ingestion_engine.nodes.node_vlm_summary import NodeVlmSummary
from kb_manage_platform.engines.ingestion_engine.state import IngestionGraphState


class KBImportWorkflow:
    """知识库导入工作流，负责节点创建、注册和路由。"""

    # 作用：保存入库依赖并初始化 LangGraph。
    def __init__(
        self,
        parser: DocumentParserPort,
        image_summarizer: ImageSummarizerPort,
        chunker: ChunkerPort,
        embedder: EmbedderPort,
        vector_index: VectorIndexPort,
        repository: DocumentRepositoryPort,
        audit: AuditPort,
    ) -> None:
        self._workflow = StateGraph(IngestionGraphState)
        self._compiled_app: Any = None
        self._init_nodes(parser, image_summarizer, chunker, embedder, vector_index, repository, audit)
        self._register_nodes()
        self._setup_routes()

    # 作用：创建入库流程节点实例。
    def _init_nodes(
        self,
        parser: DocumentParserPort,
        image_summarizer: ImageSummarizerPort,
        chunker: ChunkerPort,
        embedder: EmbedderPort,
        vector_index: VectorIndexPort,
        repository: DocumentRepositoryPort,
        audit: AuditPort,
    ) -> None:
        """初始化入库节点。"""
        self.node_entry = NodeEntry()
        self.node_mineru_parse = NodeMineruParse(parser)
        self.node_vlm_summary = NodeVlmSummary(image_summarizer)
        self.node_document_split = NodeDocumentSplit(chunker)
        self.node_embedding = NodeEmbedding(embedder)
        self.node_milvus_import = MilvusImportNode(vector_index)
        self.node_index_version = NodeIndexVersion(repository)
        self.node_import_audit = NodeImportAudit(audit)

    # 作用：注册全部入库节点。
    def _register_nodes(self) -> None:
        """注册节点到 LangGraph。"""
        self._workflow.add_node("node_entry", self.node_entry)
        self._workflow.add_node("node_mineru_parse", self.node_mineru_parse)
        self._workflow.add_node("node_vlm_summary", self.node_vlm_summary)
        self._workflow.add_node("node_document_split", self.node_document_split)
        self._workflow.add_node("node_embedding", self.node_embedding)
        self._workflow.add_node("node_milvus_import", self.node_milvus_import)
        self._workflow.add_node("node_index_version", self.node_index_version)
        self._workflow.add_node("node_import_audit", self.node_import_audit)

    # 作用：设置顺序入库流程。
    def _setup_routes(self) -> None:
        """配置入库流程边。"""
        self._workflow.set_entry_point("node_entry")
        self._workflow.add_edge("node_entry", "node_mineru_parse")
        self._workflow.add_edge("node_mineru_parse", "node_vlm_summary")
        self._workflow.add_edge("node_vlm_summary", "node_document_split")
        self._workflow.add_edge("node_document_split", "node_embedding")
        self._workflow.add_edge("node_embedding", "node_milvus_import")
        self._workflow.add_edge("node_milvus_import", "node_index_version")
        self._workflow.add_edge("node_index_version", "node_import_audit")
        self._workflow.add_edge("node_import_audit", END)

    # 作用：懒加载编译 LangGraph。
    def compile(self) -> Any:
        """编译并返回入库工作流。"""
        if self._compiled_app is None:
            self._compiled_app = self._workflow.compile()
        return self._compiled_app

    # 作用：异步执行入库流程。
    async def ainvoke(self, initial_state: IngestionGraphState) -> IngestionGraphState:
        """执行入库图。"""
        return await self.compile().ainvoke(initial_state)