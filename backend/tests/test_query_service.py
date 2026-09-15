"""验证问答服务身份加载、历史读取和会话写入。"""

import pytest

from kb_manage_platform.domain.models import AnswerResult, ConversationMessage, UserContext
from kb_manage_platform.services.query_service import QueryService


class FakeIdentityRepository:
    """身份仓储测试桩。"""

    # 作用：返回固定用户上下文。
    async def get_user_context(self, user_id: str) -> UserContext:
        """返回固定用户。"""
        return UserContext(
            user_id=user_id,
            department_id="finance",
            department_path=("company", "finance"),
            role_ids=("viewer",),
            permission_version=3,
        )


class FakeConversationRepository:
    """会话仓储测试桩。"""

    # 作用：初始化测试记录。
    def __init__(self) -> None:
        self.saved = False

    # 作用：返回最近一条历史消息。
    async def get_recent_messages(self, session_id: str, user_id: str, limit: int):
        """返回历史消息。"""
        return (ConversationMessage(role="user", content="上一轮问题"),)

    # 作用：记录保存动作。
    async def save_turn(self, request_id, session_id, user_id, question, answer) -> None:
        """记录保存。"""
        self.saved = True


class FakeQueryWorkflow:
    """问答引擎测试桩。"""

    # 作用：记录收到的初始状态并返回答案。
    async def ainvoke(self, state):
        """返回固定答案。"""
        assert state["request"].user.permission_version == 3
        assert state["request"].history[0].content == "上一轮问题"
        return {"answer": AnswerResult(answer="测试回答")}


# 作用：验证问答服务完整编排。
@pytest.mark.asyncio
async def test_query_service_loads_identity_and_saves_turn() -> None:
    """验证身份、历史读取和回答持久化。"""
    conversation = FakeConversationRepository()
    service = QueryService(FakeQueryWorkflow(), FakeIdentityRepository(), conversation)
    request_id, answer = await service.ask("测试问题", "session-1", "user-1")
    assert request_id
    assert answer.answer == "测试回答"
    assert conversation.saved is True