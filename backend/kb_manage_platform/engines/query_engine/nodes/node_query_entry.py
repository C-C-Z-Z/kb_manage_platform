"""实现问题接收与校验节点。"""

from typing import Any

from kb_manage_platform.engines.query_engine.base import QueryNodeBase
from kb_manage_platform.engines.query_engine.state import QaGraphState


class NodeQueryEntry(QueryNodeBase):
    """校验用户状态并规范化问题。"""

    name = "node_query_entry"

    # 作用：校验用户状态和问题内容。
    async def process(self, state: QaGraphState) -> dict[str, Any]:
        """返回规范化后的问题。"""
        request = state["request"]
        if not request.user.is_active:
            raise PermissionError("user is inactive")
        question = request.question.strip()
        if not question:
            raise ValueError("question must not be empty")
        return {"normalized_question": question}