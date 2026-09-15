"""实现问答审计节点。"""

from typing import Any

from kb_manage_platform.domain.ports import AuditPort
from kb_manage_platform.engines.query_engine.base import QueryNodeBase
from kb_manage_platform.engines.query_engine.state import QaGraphState


class NodeAudit(QueryNodeBase):
    """记录问答链路摘要和 FAQ/缺口挖掘所需字段。"""

    name = "node_audit"

    # 作用：保存审计端口。
    def __init__(self, audit: AuditPort) -> None:
        self._audit = audit

    # 作用：记录问答完成事件。
    async def process(self, state: QaGraphState) -> dict[str, Any]:
        """写入审计信息。"""
        request = state["request"]
        answer = state.get("answer")
        rrf_candidates = state.get("rrf_candidates", [])
        allowed_candidates = state.get("allowed_candidates", [])
        final_candidates = state.get("final_candidates", [])
        authorized_ids = sorted({item.knowledge_id for item in allowed_candidates})
        blocked_ids = sorted(
            {item.knowledge_id for item in rrf_candidates}
            - {item.knowledge_id for item in allowed_candidates}
        )
        signatures = sorted(
            {
                str(item.metadata.get("permission_signature", ""))
                for item in allowed_candidates
                if item.metadata.get("permission_signature")
            }
        )
        await self._audit.record(
            "qa.completed",
            {
                "request_id": request.request_id,
                "session_id": request.session_id,
                "user_id": request.user.user_id,
                "department_id": request.user.department_id,
                "question": state.get("normalized_question", request.question),
                "faq_hit": bool(state.get("faq_answer")),
                "recall_count": len(rrf_candidates),
                "authorized_count": len(allowed_candidates),
                "blocked_count": len(blocked_ids),
                "final_count": len(final_candidates),
                "authorized_knowledge_ids": authorized_ids,
                "blocked_knowledge_ids": blocked_ids,
                "permission_signatures": signatures,
                "answer_excerpt": answer.answer[:500] if answer else "",
                "has_answer": answer is not None,
            },
        )
        return {}