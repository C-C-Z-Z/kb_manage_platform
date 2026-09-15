"""实现 Reciprocal Rank Fusion 排名融合规则。"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace

from kb_manage_platform.domain.models import RetrievedCandidate


class RrfFuser:
    """对多路检索结果执行 RRF 融合，不依赖 Milvus 或模型 SDK。"""

    # 作用：保存 RRF 平滑参数。
    def __init__(self, rank_constant: int = 60) -> None:
        if rank_constant <= 0:
            raise ValueError("rank_constant must be positive")
        self._rank_constant = rank_constant

    # 作用：按路线排名计算融合分数并返回全局排序候选。
    def fuse(
        self,
        routes: Mapping[str, Sequence[RetrievedCandidate]],
        top_k: int,
    ) -> list[RetrievedCandidate]:
        """融合多路候选，重复切片按 chunk_id 去重。"""
        scores: dict[str, float] = defaultdict(float)
        candidates: dict[str, RetrievedCandidate] = {}
        sources: dict[str, list[str]] = defaultdict(list)

        for route_name, route_candidates in routes.items():
            for rank, candidate in enumerate(route_candidates, start=1):
                candidates.setdefault(candidate.chunk_id, candidate)
                sources[candidate.chunk_id].append(route_name)
                scores[candidate.chunk_id] += 1.0 / (self._rank_constant + rank)

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        result: list[RetrievedCandidate] = []
        for chunk_id, score in ranked[:top_k]:
            base = candidates[chunk_id]
            result.append(
                replace(
                    base,
                    score=score,
                    source="rrf:" + ",".join(sources[chunk_id]),
                )
            )
        return result