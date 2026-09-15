"""记录 FAQ 与知识缺口流程审计结果。"""

from typing import Any

from kb_manage_platform.domain.models import FaqGapResult
from kb_manage_platform.domain.ports import AuditPort
from kb_manage_platform.engines.faq_gap_engine.base import FaqGapNodeBase
from kb_manage_platform.engines.faq_gap_engine.state import FaqGapGraphState


class NodeFaqGapAudit(FaqGapNodeBase):
    """写入闭环流程审计并组装结果。"""

    name = "node_faq_gap_audit"

    # 作用：保存审计端口。
    def __init__(self, audit: AuditPort) -> None:
        self._audit = audit

    # 作用：记录处理数量并返回结果。
    async def process(self, state: FaqGapGraphState) -> dict[str, Any]:
        """返回流程结果。"""
        command = state["command"]
        candidates = state.get("candidates", ())
        gaps = state.get("gaps", ())
        draft_id = str(state.get("draft_id", ""))
        result = FaqGapResult(
            action=command.action,
            processed_count=len(candidates) if candidates else len(gaps),
            candidate_ids=tuple(item.candidate_id for item in candidates),
            gap_ids=tuple(item.gap_id for item in gaps),
            draft_id=draft_id,
        )
        await self._audit.record(
            f"faq_gap.{command.action.value}",
            {
                "request_id": command.request_id,
                "user_id": command.operator_id,
                "processed_count": result.processed_count,
                "candidate_ids": list(result.candidate_ids),
                "gap_ids": list(result.gap_ids),
                "draft_id": result.draft_id,
            },
        )
        return {"result": result}