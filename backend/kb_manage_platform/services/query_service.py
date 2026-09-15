"""提供知识问答应用服务。"""

import time
from uuid import uuid4

from kb_manage_platform.domain.models import AnswerResult, QuestionRequest, UserContext
from kb_manage_platform.domain.ports import (
    AuditPort,
    ConversationRepositoryPort,
    IdentityRepositoryPort,
)
from kb_manage_platform.engines.query_engine.main_graph import KBQueryWorkflow


class QueryService:
    """编排问答请求、身份上下文、会话历史和查询引擎。"""

    def __init__(
        self,
        workflow: KBQueryWorkflow,
        identity_repository: IdentityRepositoryPort,
        conversation_repository: ConversationRepositoryPort,
        audit: AuditPort | None = None,
    ) -> None:
        self._workflow = workflow
        self._identity_repository = identity_repository
        self._conversation_repository = conversation_repository
        self._audit = audit

    async def ask(
        self,
        question: str,
        session_id: str,
        user: UserContext | str,
    ) -> tuple[str, AnswerResult]:
        """返回请求 ID 和回答结果。"""
        request_id = str(uuid4())
        session_id = session_id or str(uuid4())
        user_context = (
            user
            if isinstance(user, UserContext)
            else await self._identity_repository.get_user_context(user)
        )
        history = await self._conversation_repository.get_recent_messages(
            session_id, user_context.user_id, limit=10
        )
        started_at = time.perf_counter()
        state = await self._workflow.ainvoke(
            {
                "request": QuestionRequest(
                    request_id=request_id,
                    session_id=session_id,
                    question=question,
                    user=user_context,
                    history=history,
                )
            }
        )
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        answer = state.get("answer", AnswerResult(answer="现有知识无法支撑该问题。"))
        await self._conversation_repository.save_turn(
            request_id=request_id,
            session_id=session_id,
            user_id=user_context.user_id,
            question=question,
            answer=answer,
        )
        if self._audit is not None:
            estimated_tokens = max(1, int((len(question) + len(answer.answer)) / 2))
            await self._audit.record(
                "qa.metrics",
                {
                    "request_id": request_id,
                    "session_id": session_id,
                    "user_id": user_context.user_id,
                    "latency_ms": elapsed_ms,
                    "estimated_tokens": estimated_tokens,
                },
            )
        return request_id, answer

    async def list_sessions(self, user_id: str):
        """返回当前用户会话列表。"""
        return await self._conversation_repository.list_sessions(user_id)

    async def list_messages(self, session_id: str, user_id: str):
        """返回当前用户指定会话的消息。"""
        return await self._conversation_repository.list_messages(session_id, user_id)

    async def rename_session(self, session_id: str, user_id: str, title: str):
        """重命名当前用户的会话。"""
        return await self._conversation_repository.rename_session(session_id, user_id, title)

    async def delete_session(self, session_id: str, user_id: str) -> None:
        """删除当前用户的会话。"""
        await self._conversation_repository.delete_session(session_id, user_id)

