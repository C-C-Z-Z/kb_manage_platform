"""校验 FAQ 与知识缺口命令。"""

from typing import Any

from kb_manage_platform.domain.models import FaqGapAction
from kb_manage_platform.engines.faq_gap_engine.base import FaqGapNodeBase
from kb_manage_platform.engines.faq_gap_engine.state import FaqGapGraphState


class NodeFaqGapEntry(FaqGapNodeBase):
    """校验动作参数。"""

    name = "node_faq_gap_entry"

    # 作用：检查审核、转建和解决所需字段。
    async def process(self, state: FaqGapGraphState) -> dict[str, Any]:
        """返回校验结果。"""
        command = state["command"]
        if command.action is FaqGapAction.REVIEW_FAQ and not command.candidate_id:
            raise ValueError("candidate_id must not be empty")
        if command.action in {FaqGapAction.CONVERT_GAP, FaqGapAction.RESOLVE_GAP} and not command.gap_id:
            raise ValueError("gap_id must not be empty")
        if command.action is FaqGapAction.CONVERT_GAP and not command.title:
            raise ValueError("title must not be empty")
        return {}