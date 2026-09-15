"""验证密码、JWT 和关键查询降级规则。"""

import pytest

from kb_manage_platform.common.errors import AuthenticationError
from kb_manage_platform.domain.models import QuestionRequest, RetrievedCandidate, UserContext
from kb_manage_platform.engines.query_engine.nodes.node_auth_filter import NodeAuthFilter
from kb_manage_platform.engines.query_engine.nodes.node_rerank import NodeRerank
from kb_manage_platform.engines.query_engine.nodes.node_search_hyde import NodeSearchHyde
from kb_manage_platform.infrastructure.adapters.security_utils import JwtTokenService, ScryptPasswordHasher


class BrokenHydeGenerator:
    """HyDE 异常测试桩。"""

    # 作用：模拟模型异常。
    async def generate(self, question: str, count: int):
        """抛出异常。"""
        raise RuntimeError("hyde unavailable")


class UnusedVectorRetriever:
    """未调用的向量检索桩。"""

    # 作用：抛出异常以确认不会被调用。
    async def retrieve(self, texts, user, top_k):
        """不应执行。"""
        raise AssertionError("should not be called")


class BrokenReranker:
    """Reranker 异常测试桩。"""

    # 作用：模拟精排异常。
    async def rerank(self, question, candidates, top_k):
        """抛出异常。"""
        raise RuntimeError("reranker unavailable")


class BrokenAuthorizer:
    """权限服务异常测试桩。"""

    # 作用：模拟权限服务异常。
    async def filter_allowed(self, user, candidates):
        """抛出异常。"""
        raise RuntimeError("authorization unavailable")


# 作用：验证 scrypt 密码和 JWT。
def test_password_and_jwt() -> None:
    """验证密码哈希和令牌签名。"""
    hasher = ScryptPasswordHasher()
    password_hash = hasher.hash("Password123")
    assert hasher.verify("Password123", password_hash)
    assert not hasher.verify("WrongPassword", password_hash)
    tokens = JwtTokenService("test-secret", 60)
    token, expires = tokens.issue("user-1", 2)
    assert expires == 60
    assert tokens.parse(token) == ("user-1", 2)
    with pytest.raises(AuthenticationError):
        tokens.parse(token + "tampered")


# 作用：验证 HyDE 失败时不影响原问答流程。
@pytest.mark.asyncio
async def test_hyde_failure_degrades() -> None:
    """验证 HyDE 失败返回空候选和警告。"""
    node = NodeSearchHyde(BrokenHydeGenerator(), UnusedVectorRetriever(), 3, 5)
    state = {
        "normalized_question": "测试问题",
        "request": QuestionRequest("r1", UserContext("u1", "d1", (), 1), "测试问题"),
    }
    result = await node.process(state)
    assert result["hyde_candidates"] == []
    assert result["warnings"] == ["hyde_retrieval_unavailable"]


# 作用：验证 Reranker 失败时回退 RRF 顺序。
@pytest.mark.asyncio
async def test_reranker_failure_degrades() -> None:
    """验证 Reranker 失败回退。"""
    candidates = [RetrievedCandidate("c1", "k1", "v1", "内容", 1.0, "rrf")]
    node = NodeRerank(BrokenReranker(), 5)
    state = {
        "normalized_question": "测试问题",
        "request": QuestionRequest("r1", UserContext("u1", "d1", (), 1), "测试问题"),
        "allowed_candidates": candidates,
    }
    result = await node.process(state)
    assert result["reranked_candidates"] == candidates
    assert result["warnings"] == ["reranker_unavailable_lexical_fallback"]


# 作用：验证鉴权服务失败时默认拒绝。
@pytest.mark.asyncio
async def test_authorization_failure_default_denies() -> None:
    """验证鉴权异常默认拒绝。"""
    node = NodeAuthFilter(BrokenAuthorizer(), "rrf_candidates", "allowed_candidates")
    state = {
        "request": QuestionRequest("r1", UserContext("u1", "d1", (), 1), "测试问题"),
        "rrf_candidates": [RetrievedCandidate("c1", "k1", "v1", "内容", 1.0, "rrf")],
    }
    result = await node.process(state)
    assert result["allowed_candidates"] == []
    assert result["warnings"] == ["authorization_unavailable_default_deny"]
