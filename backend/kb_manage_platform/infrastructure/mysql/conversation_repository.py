"""使用 SQLAlchemy 保存和读取问答会话记录。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.domain.models import (AnswerResult, ConversationMessage, ConversationMessageView, ConversationSession, RetrievedCandidate)
from kb_manage_platform.infrastructure.mysql.models import (
    QaCitationModel,
    QaMessageModel,
    QaSessionModel,
)


class MysqlConversationRepository:
    """MySQL 问答会话仓储。"""

    # 作用：保存异步会话工厂。
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：读取指定用户会话的最近消息。
    async def get_recent_messages(
        self, session_id: str, user_id: str, limit: int
    ) -> tuple[ConversationMessage, ...]:
        """读取最近会话消息。"""
        if not session_id:
            return ()
        async with self._session_factory() as session:
            session_model = await session.get(QaSessionModel, session_id)
            if session_model is None:
                return ()
            if session_model.user_id != user_id:
                raise PermissionError("session does not belong to current user")
            rows = (
                await session.scalars(
                    select(QaMessageModel)
                    .where(QaMessageModel.session_id == session_id)
                    .order_by(QaMessageModel.id.desc())
                    .limit(limit)
                )
            ).all()
        return tuple(
            ConversationMessage(
                role=row.role,
                content=row.content,
                request_id=row.request_id,
            )
            for row in reversed(rows)
        )

    # 作用：查询指定用户的会话列表。
    async def list_sessions(self, user_id: str) -> tuple[ConversationSession, ...]:
        """按更新时间倒序返回会话摘要。"""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(QaSessionModel)
                    .where(QaSessionModel.user_id == user_id)
                    .order_by(QaSessionModel.updated_at.desc(), QaSessionModel.session_id.desc())
                )
            ).all()
        return tuple(
            ConversationSession(
                session_id=row.session_id,
                title=row.title,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        )

    # 作用：查询指定会话的消息及其引用。
    async def list_messages(
        self, session_id: str, user_id: str
    ) -> tuple[ConversationMessageView, ...]:
        """按时间正序返回会话消息。"""
        async with self._session_factory() as session:
            session_model = await session.get(QaSessionModel, session_id)
            if session_model is None:
                raise LookupError(f"session not found: {session_id}")
            if session_model.user_id != user_id:
                raise PermissionError("session does not belong to current user")
            messages = (
                await session.scalars(
                    select(QaMessageModel)
                    .where(QaMessageModel.session_id == session_id)
                    .order_by(QaMessageModel.id.asc())
                )
            ).all()
            message_ids = tuple(row.message_id for row in messages)
            citations = (
                await session.scalars(
                    select(QaCitationModel).where(QaCitationModel.message_id.in_(message_ids))
                )
            ).all() if message_ids else []
        citations_by_message: dict[str, list[RetrievedCandidate]] = {}
        for row in citations:
            citations_by_message.setdefault(row.message_id, []).append(
                RetrievedCandidate(
                    chunk_id=row.chunk_id,
                    knowledge_id=row.knowledge_id,
                    version_id=row.version_id,
                    content=row.snippet,
                    score=0.0,
                    source="history",
                    metadata={"title": row.title, "section_path": row.section_path},
                )
            )
        return tuple(
            ConversationMessageView(
                message_id=row.message_id,
                role=row.role,
                content=row.content,
                request_id=row.request_id,
                created_at=row.created_at,
                citations=tuple(citations_by_message.get(row.message_id, [])),
            )
            for row in messages
        )

    # 作用：重命名当前用户的会话。
    async def rename_session(
        self, session_id: str, user_id: str, title: str
    ) -> ConversationSession:
        """更新会话标题。"""
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("session title must not be empty")
        async with self._session_factory() as session:
            model = await session.get(QaSessionModel, session_id)
            if model is None:
                raise LookupError(f"session not found: {session_id}")
            if model.user_id != user_id:
                raise PermissionError("session does not belong to current user")
            model.title = normalized_title[:255]
            await session.commit()
            await session.refresh(model)
            return ConversationSession(
                session_id=model.session_id,
                title=model.title,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

    # 作用：删除当前用户的会话及消息引用。
    async def delete_session(self, session_id: str, user_id: str) -> None:
        """删除会话、消息和引用。"""
        async with self._session_factory() as session:
            model = await session.get(QaSessionModel, session_id)
            if model is None:
                raise LookupError(f"session not found: {session_id}")
            if model.user_id != user_id:
                raise PermissionError("session does not belong to current user")
            message_ids = tuple(
                await session.scalars(
                    select(QaMessageModel.message_id).where(QaMessageModel.session_id == session_id)
                )
            )
            if message_ids:
                await session.execute(
                    delete(QaCitationModel).where(QaCitationModel.message_id.in_(message_ids))
                )
                await session.execute(
                    delete(QaMessageModel).where(QaMessageModel.session_id == session_id)
                )
            await session.delete(model)
            await session.commit()

    # 作用：保存一轮用户问题和助手回答。
    async def save_turn(
        self,
        request_id: str,
        session_id: str,
        user_id: str,
        question: str,
        answer: AnswerResult,
    ) -> None:
        """写入 qa_session、qa_message 和 qa_citation。"""
        async with self._session_factory() as session:
            session_model = await session.get(QaSessionModel, session_id)
            if session_model is None:
                session_model = QaSessionModel(
                    session_id=session_id,
                    user_id=user_id,
                    title=question[:100],
                )
                session.add(session_model)
            elif session_model.user_id != user_id:
                raise PermissionError("session does not belong to current user")
            else:
                session_model.updated_at = datetime.now(UTC)

            session.add(
                QaMessageModel(
                    message_id=str(uuid4()),
                    session_id=session_id,
                    user_id=user_id,
                    request_id=request_id,
                    role="user",
                    content=question,
                )
            )
            answer_message_id = str(uuid4())
            session.add(
                QaMessageModel(
                    message_id=answer_message_id,
                    session_id=session_id,
                    user_id=user_id,
                    request_id=request_id,
                    role="assistant",
                    content=answer.answer,
                )
            )
            for citation in answer.citations:
                session.add(
                    QaCitationModel(
                        message_id=answer_message_id,
                        knowledge_id=citation.knowledge_id,
                        version_id=citation.version_id,
                        chunk_id=citation.chunk_id,
                        title=str(citation.metadata.get("title", "")),
                        section_path=str(citation.metadata.get("section_path", "")),
                        snippet=citation.content[:500],
                    )
                )
            await session.commit()
