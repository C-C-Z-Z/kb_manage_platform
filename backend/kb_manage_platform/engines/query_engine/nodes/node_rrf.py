"""实现 RRF 排名融合节点。"""

from typing import Any

from kb_manage_platform.domain.services.rrf import RrfFuser
from kb_manage_platform.engines.query_engine.base import QueryNodeBase
from kb_manage_platform.engines.query_engine.state import QaGraphState


class NodeRrf(QueryNodeBase):
    """融合路线 A 与路线 B。"""

    name = "node_rrf"

    # 作用：保存 RRF 融合器和输出数量。
    def __init__(self, fuser: RrfFuser, top_k: int) -> None:
        self._fuser = fuser
        self._top_k = top_k

    # 作用：融合两路候选。
    async def process(self, state: QaGraphState) -> dict[str, Any]:
        """返回 RRF 候选。"""
        return {
            "rrf_candidates": self._fuser.fuse(
                {
                    "original": state.get("original_candidates", []),
                    "hyde": state.get("hyde_candidates", []),
                },
                self._top_k,
            )
        }