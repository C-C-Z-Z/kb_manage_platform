"""问答 API 的请求和响应模型。"""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """问答请求。"""

    question: str = Field(..., min_length=1)
    session_id: str = Field(default="")


class QueryCitation(BaseModel):
    """回答引用的授权知识切片。"""

    chunk_id: str
    knowledge_id: str
    version_id: str
    content: str
    score: float
    source: str


class QueryResponse(BaseModel):
    """问答响应。"""

    request_id: str
    answer: str
    warnings: list[str] = Field(default_factory=list)
    citations: list[QueryCitation] = Field(default_factory=list)


class RenameSessionRequest(BaseModel):
    """会话重命名请求。"""

    title: str = Field(..., min_length=1, max_length=255)


class SessionResponse(BaseModel):
    """会话列表响应。"""

    session_id: str
    title: str
    created_at: str = ""
    updated_at: str = ""


class MessageResponse(BaseModel):
    """会话消息响应。"""

    message_id: str
    role: str
    content: str
    request_id: str
    created_at: str = ""
    citations: list[QueryCitation] = Field(default_factory=list)
