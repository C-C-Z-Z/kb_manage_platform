"""知识问答、会话历史和 SSE 路由。"""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from kb_manage_platform.api.dependencies import (
    QueryServiceDep,
    QueryUserDep,
    SessionReadUserDep,
)
from kb_manage_platform.api.schemas.query import (
    MessageResponse,
    QueryCitation,
    QueryRequest,
    QueryResponse,
    RenameSessionRequest,
    SessionResponse,
)
from kb_manage_platform.common.errors import AppError
from kb_manage_platform.domain.models import RetrievedCandidate

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(
    payload: QueryRequest,
    user: QueryUserDep,
    service: QueryServiceDep,
) -> QueryResponse:
    """执行非流式问答。"""
    request_id, answer = await service.ask(payload.question, payload.session_id, user)
    return QueryResponse(
        request_id=request_id,
        answer=answer.answer,
        warnings=list(answer.warnings),
        citations=[_citation(candidate) for candidate in answer.citations],
    )


@router.post("/query/stream")
async def query_stream(
    payload: QueryRequest,
    user: QueryUserDep,
    service: QueryServiceDep,
) -> StreamingResponse:
    """以单个 delta 的 SSE 协议返回问答结果。"""

    async def event_stream() -> AsyncIterator[str]:
        try:
            request_id, answer = await service.ask(payload.question, payload.session_id, user)
            yield _event("meta", {"request_id": request_id, "session_id": payload.session_id})
            for warning in answer.warnings:
                yield _event("warning", {"message": warning})
            yield _event("delta", {"content": answer.answer})
            for candidate in answer.citations:
                yield _event("citation", _citation(candidate).model_dump())
            estimated_tokens = max(1, int((len(payload.question) + len(answer.answer)) / 2))
            yield _event("usage", {"estimated_tokens": estimated_tokens})
            yield _event("done", {"request_id": request_id})
        except AppError as exc:
            yield _event(
                "error",
                {"code": exc.code, "message": exc.message, "retryable": exc.status_code >= 500},
            )
        except Exception:
            yield _event(
                "error",
                {"code": "INTERNAL_ERROR", "message": "generation failed", "retryable": True},
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    user: SessionReadUserDep,
    service: QueryServiceDep,
) -> list[SessionResponse]:
    """返回当前用户会话列表。"""
    sessions = await service.list_sessions(user.user_id)
    return [
        SessionResponse(
            session_id=item.session_id,
            title=item.title,
            created_at=item.created_at.isoformat() if item.created_at else "",
            updated_at=item.updated_at.isoformat() if item.updated_at else "",
        )
        for item in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: str,
    user: SessionReadUserDep,
    service: QueryServiceDep,
) -> list[MessageResponse]:
    """返回当前用户会话的完整消息。"""
    messages = await service.list_messages(session_id, user.user_id)
    return [
        MessageResponse(
            message_id=item.message_id,
            role=item.role,
            content=item.content,
            request_id=item.request_id,
            created_at=item.created_at.isoformat() if item.created_at else "",
            citations=[_citation(candidate) for candidate in item.citations],
        )
        for item in messages
    ]


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def rename_session(
    session_id: str,
    payload: RenameSessionRequest,
    user: SessionReadUserDep,
    service: QueryServiceDep,
) -> SessionResponse:
    """重命名当前用户的会话。"""
    item = await service.rename_session(session_id, user.user_id, payload.title)
    return SessionResponse(
        session_id=item.session_id,
        title=item.title,
        created_at=item.created_at.isoformat() if item.created_at else "",
        updated_at=item.updated_at.isoformat() if item.updated_at else "",
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: SessionReadUserDep,
    service: QueryServiceDep,
) -> None:
    """删除当前用户的会话。"""
    await service.delete_session(session_id, user.user_id)


def _citation(candidate: RetrievedCandidate) -> QueryCitation:
    """将领域候选转换为 API 引用模型。"""
    return QueryCitation(
        chunk_id=candidate.chunk_id,
        knowledge_id=candidate.knowledge_id,
        version_id=candidate.version_id,
        content=candidate.content,
        score=candidate.score,
        source=candidate.source,
    )


def _event(event: str, data: dict[str, object]) -> str:
    """返回标准 SSE 文本。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
