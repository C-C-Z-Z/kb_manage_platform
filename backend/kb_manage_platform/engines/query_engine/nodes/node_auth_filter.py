"""实现四维数据权限过滤节点。"""

from typing import Any

from kb_manage_platform.domain.ports import AuthorizationPort
from kb_manage_platform.engines.query_engine.base import QueryNodeBase
from kb_manage_platform.engines.query_engine.state import QaGraphState


class NodeAuthFilter(QueryNodeBase):
    """按阶段过滤候选知识。"""

    name = "node_auth_filter"

    # 作用：保存鉴权端口、输入字段和输出字段。
    def __init__(self, authorizer: AuthorizationPort, input_key: str, output_key: str) -> None:
        self._authorizer = authorizer
        self._input_key = input_key
        self._output_key = output_key

    # 作用：过滤无权候选并返回指定状态字段。
    async def process(self, state: QaGraphState) -> dict[str, Any]:
        """返回授权候选。"""
        try:
            allowed = await self._authorizer.filter_allowed(
                state["request"].user, state.get(self._input_key, [])
            )
        except Exception:
            return {self._output_key: [], "warnings": ["authorization_unavailable_default_deny"]}
        return {self._output_key: list(allowed)}