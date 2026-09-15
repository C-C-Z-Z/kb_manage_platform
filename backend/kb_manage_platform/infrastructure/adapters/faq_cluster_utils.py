"""使用 BGE-M3 向量执行问答文本语义聚类。"""

import math
from collections.abc import Sequence

from kb_manage_platform.domain.models import QaLogRecord, QuestionCluster
from kb_manage_platform.domain.ports import EmbedderPort


class EmbeddingQuestionClusterer:
    """使用 EmbedderPort 生成向量并按余弦相似度贪心聚类。"""

    # 作用：保存复用的 BGE-M3 等 Embedding 端口。
    def __init__(self, embedder: EmbedderPort) -> None:
        self._embedder = embedder

    # 作用：将相似问题聚合为问题簇。
    async def cluster(
        self,
        logs: Sequence[QaLogRecord],
        threshold: float,
    ) -> tuple[QuestionCluster, ...]:
        """返回语义相似问题簇。"""
        if not logs:
            return ()
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("similarity threshold must be between 0 and 1")

        vectors = await self._embed_questions(tuple(log.question for log in logs))
        clusters: list[list[tuple[QaLogRecord, tuple[float, ...]]]] = []
        for log, vector in zip(logs, vectors, strict=True):
            target = self._find_cluster(vector, clusters, threshold)
            if target is None:
                clusters.append([(log, vector)])
            else:
                target.append((log, vector))

        return tuple(
            QuestionCluster(
                representative_question=max(
                    (item for item, _ in items),
                    key=lambda item: len(item.question),
                ).question,
                logs=tuple(item for item, _ in items),
                similarity=max(
                    (
                        self._cosine_similarity(items[0][1], vector)
                        for _, vector in items[1:]
                    ),
                    default=1.0,
                ),
            )
            for items in clusters
        )

    # 作用：批量生成并规范化问题向量。
    async def _embed_questions(
        self,
        questions: tuple[str, ...],
    ) -> tuple[tuple[float, ...], ...]:
        """返回与输入等长的单位向量。"""
        raw_vectors = await self._embedder.embed(questions)
        if len(raw_vectors) != len(questions):
            raise RuntimeError("embedding response size does not match question count")

        vectors = tuple(self._normalize(vector) for vector in raw_vectors)
        dimension = len(vectors[0]) if vectors else 0
        if any(len(vector) != dimension for vector in vectors):
            raise RuntimeError("embedding vectors must have the same dimension")
        return vectors

    # 作用：查找与问题向量相似度达到门槛的已有簇。
    def _find_cluster(
        self,
        vector: tuple[float, ...],
        clusters: Sequence[Sequence[tuple[QaLogRecord, tuple[float, ...]]]],
        threshold: float,
    ) -> list[tuple[QaLogRecord, tuple[float, ...]]] | None:
        """返回匹配簇。"""
        for items in clusters:
            if self._cosine_similarity(vector, items[0][1]) >= threshold:
                return items
        return None

    # 作用：将向量归一化，使点积等价于余弦相似度。
    @staticmethod
    def _normalize(vector: Sequence[float]) -> tuple[float, ...]:
        """返回单位向量。"""
        values = tuple(float(value) for value in vector)
        if not values:
            raise ValueError("embedding vector must not be empty")
        norm = math.sqrt(math.fsum(value * value for value in values))
        if norm == 0.0:
            raise ValueError("embedding vector norm must not be zero")
        return tuple(value / norm for value in values)

    # 作用：计算两个单位向量的余弦相似度。
    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        """返回 0 到 1 范围内的余弦相似度。"""
        if len(left) != len(right):
            raise ValueError("embedding vectors must have the same dimension")
        score = math.fsum(a * b for a, b in zip(left, right, strict=True))
        return max(0.0, min(1.0, score))