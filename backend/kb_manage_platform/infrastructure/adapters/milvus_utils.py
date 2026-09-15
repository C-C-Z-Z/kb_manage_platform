"""实现 Milvus 集合管理、Dense Vector 与 BM25 索引写入。"""

import asyncio
from collections.abc import Sequence
from typing import Any

from pymilvus import (
    AnnSearchRequest,
    DataType,
    Function,
    MilvusClient,
    RRFRanker,
)
from pymilvus.client.types import FunctionType
from pymilvus.exceptions import MilvusException

from kb_manage_platform.common.logger import logger
from kb_manage_platform.domain.models import KnowledgeChunk, RetrievedCandidate


class MilvusStore:
    """封装 Milvus 客户端、集合创建、写入和检索细节。"""

    _OUTPUT_FIELDS = ["chunk_id", "knowledge_id", "version_id", "content", "section_path", "image_summary"]

    # 作用：保存连接、集合和索引参数，连接在首次使用时建立。
    def __init__(
        self,
        uri: str,
        collection_name: str,
        vector_dim: int,
        metric_type: str = "COSINE",
        index_type: str = "HNSW",
        user: str = "",
        password: str = "",
        database: str = "default",
    ) -> None:
        self._uri = uri
        self._collection_name = collection_name
        self._vector_dim = vector_dim
        self._metric_type = metric_type.upper()
        self._index_type = index_type.upper()
        self._user = user
        self._password = password
        self._database = database
        self._client: MilvusClient | None = None
        self._collection_lock = asyncio.Lock()

    # 作用：写入切片、Dense Vector 和由 BM25 自动生成的稀疏向量。
    async def upsert(self, chunks: Sequence[KnowledgeChunk], vectors: Sequence[Sequence[float]]) -> None:
        """批量 upsert 知识切片。"""
        if not chunks:
            return
        if len(chunks) != len(vectors):
            raise ValueError("chunk count and vector count do not match")
        for vector in vectors:
            if len(vector) != self._vector_dim:
                raise ValueError(
                    f"vector dimension mismatch: expected {self._vector_dim}, got {len(vector)}"
                )
        await self._ensure_collection()
        rows = [
            {
                "chunk_id": chunk.chunk_id,
                "knowledge_id": chunk.knowledge_id,
                "version_id": chunk.version_id,
                "content": chunk.content,
                "section_path": chunk.section_path,
                "image_summary": chunk.image_summary,
                "dense_vector": list(vector),
            }
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        client = self._require_client()
        await asyncio.to_thread(client.upsert, self._collection_name, rows)

    # 作用：执行 Dense Vector 检索。
    async def search_dense(
        self,
        vector: Sequence[float],
        top_k: int,
    ) -> list[RetrievedCandidate]:
        """返回 Dense Vector 候选。"""
        await self._ensure_collection()
        client = self._require_client()
        results = await asyncio.to_thread(
            client.search,
            collection_name=self._collection_name,
            data=[list(vector)],
            anns_field="dense_vector",
            limit=max(1, top_k),
            output_fields=self._OUTPUT_FIELDS,
            search_params={"metric_type": self._metric_type},
        )
        return self._to_candidates(results, "dense")

    # 作用：执行 Dense Vector 与 BM25 稀疏向量混合检索。
    async def hybrid_search(
        self,
        vector: Sequence[float],
        question: str,
        top_k: int,
    ) -> list[RetrievedCandidate]:
        """返回 Milvus 原生 RRF 融合后的候选。"""
        await self._ensure_collection()
        client = self._require_client()
        limit = max(1, top_k)
        requests = [
            AnnSearchRequest(
                data=[list(vector)],
                anns_field="dense_vector",
                param={"metric_type": self._metric_type},
                limit=limit,
            ),
            AnnSearchRequest(
                data=[question],
                anns_field="sparse_vector",
                param={"metric_type": "BM25"},
                limit=limit,
            ),
        ]
        try:
            results = await asyncio.to_thread(
                client.hybrid_search,
                collection_name=self._collection_name,
                reqs=requests,
                ranker=RRFRanker(k=60),
                limit=limit,
                output_fields=self._OUTPUT_FIELDS,
            )
            return self._to_candidates(results, "hybrid")
        except MilvusException as exc:
            logger.warning("Milvus BM25 hybrid search failed, fallback to dense: %s", exc)
            return await self.search_dense(vector, limit)

    # 作用：读取指定知识单元的全部切片，供管理端预览。
    async def list_chunks(self, knowledge_id: str) -> list[KnowledgeChunk]:
        """返回知识单元的全部切片。"""
        await self._ensure_collection()
        client = self._require_client()
        rows = await asyncio.to_thread(
            client.query,
            collection_name=self._collection_name,
            filter=f'knowledge_id == "{knowledge_id}"',
            output_fields=self._OUTPUT_FIELDS,
        )
        return [
            KnowledgeChunk(
                chunk_id=str(row.get("chunk_id", "")),
                knowledge_id=str(row.get("knowledge_id", "")),
                version_id=str(row.get("version_id", "")),
                content=str(row.get("content", "")),
                section_path=str(row.get("section_path", "")),
                image_summary=str(row.get("image_summary", "")),
            )
            for row in rows
        ]

    # 作用：删除指定知识单元的全部向量切片。
    async def delete_knowledge(self, knowledge_id: str) -> None:
        """按知识 ID 删除 Milvus 数据。"""
        await self._ensure_collection()
        client = self._require_client()
        await asyncio.to_thread(
            client.delete,
            collection_name=self._collection_name,
            filter=f'knowledge_id == "{knowledge_id}"',
        )

    # 作用：延迟获取 Milvus 客户端。
    def _require_client(self) -> MilvusClient:
        """返回已初始化的客户端。"""
        if self._client is None:
            raise RuntimeError("Milvus client is not initialized")
        return self._client

    # 作用：创建或复用 Milvus 集合。
    async def _ensure_collection(self) -> None:
        """幂等创建 Dense 与 BM25 集合。"""
        async with self._collection_lock:
            client = self._get_or_create_client()
            exists = await asyncio.to_thread(client.has_collection, self._collection_name)
            if exists:
                return
            schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
            schema.add_field("chunk_id", DataType.VARCHAR, is_primary=True, max_length=128)
            schema.add_field("knowledge_id", DataType.VARCHAR, max_length=128)
            schema.add_field("version_id", DataType.VARCHAR, max_length=128)
            schema.add_field(
                "content",
                DataType.VARCHAR,
                max_length=65535,
                enable_analyzer=True,
                analyzer_params={"type": "chinese"},
            )
            schema.add_field("section_path", DataType.VARCHAR, max_length=1024)
            schema.add_field("image_summary", DataType.VARCHAR, max_length=65535)
            schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=self._vector_dim)
            schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)
            schema.add_function(
                Function(
                    name="content_bm25",
                    function_type=FunctionType.BM25,
                    input_field_names=["content"],
                    output_field_names=["sparse_vector"],
                )
            )
            index_params = client.prepare_index_params()
            dense_params: dict[str, Any] = {}
            if self._index_type == "HNSW":
                dense_params = {"M": 16, "efConstruction": 200}
            index_params.add_index(
                field_name="dense_vector",
                index_type=self._index_type,
                metric_type=self._metric_type,
                params=dense_params,
            )
            index_params.add_index(
                field_name="sparse_vector",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="BM25",
            )
            await asyncio.to_thread(
                client.create_collection,
                collection_name=self._collection_name,
                schema=schema,
                index_params=index_params,
            )

    # 作用：创建或返回线程安全的 Milvus 客户端。
    def _get_or_create_client(self) -> MilvusClient:
        """返回 MilvusClient。"""
        if self._client is None:
            token = f"{self._user}:{self._password}" if self._user else ""
            self._client = MilvusClient(
                uri=self._uri,
                user=self._user,
                password=self._password,
                token=token,
                db_name=self._database,
            )
        return self._client

    # 作用：将 Milvus 返回结构转换为领域候选。
    @classmethod
    def _to_candidates(
        cls,
        results: Sequence[Sequence[dict[str, Any]]],
        source: str,
    ) -> list[RetrievedCandidate]:
        """返回去重并按分数降序排列的候选。"""
        if not results:
            return []
        candidates: dict[str, RetrievedCandidate] = {}
        for row in results[0]:
            entity = row.get("entity", row)
            chunk_id = str(entity.get("chunk_id", row.get("id", "")))
            if not chunk_id:
                continue
            score = float(row.get("distance", row.get("score", 0.0)))
            candidate = RetrievedCandidate(
                chunk_id=chunk_id,
                knowledge_id=str(entity.get("knowledge_id", "")),
                version_id=str(entity.get("version_id", "")),
                content=str(entity.get("content", "")),
                score=score,
                source=source,
                metadata={
                    "section_path": entity.get("section_path", ""),
                    "image_summary": entity.get("image_summary", ""),
                },
            )
            existing = candidates.get(chunk_id)
            if existing is None or candidate.score > existing.score:
                candidates[chunk_id] = candidate
        return sorted(candidates.values(), key=lambda item: item.score, reverse=True)


class MilvusVectorIndex:
    """Milvus 索引写入适配器。"""

    # 作用：注入共享 Milvus 存储实现。
    def __init__(self, store: MilvusStore) -> None:
        self._store = store

    # 作用：写入切片、Dense Vector 和 BM25 数据。
    async def upsert(self, chunks: Sequence[KnowledgeChunk], vectors: Sequence[Sequence[float]]) -> None:
        """写入或更新 Milvus。"""
        await self._store.upsert(chunks, vectors)

    # 作用：读取指定知识单元的全部切片。
    async def list_chunks(self, knowledge_id: str) -> Sequence[KnowledgeChunk]:
        """读取 Milvus 切片。"""
        return await self._store.list_chunks(knowledge_id)

    # 作用：删除指定知识单元的全部向量。
    async def delete_knowledge(self, knowledge_id: str) -> None:
        """删除 Milvus 知识数据。"""
        await self._store.delete_knowledge(knowledge_id)