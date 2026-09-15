"""实现 Redis FAQ 缓存和 MySQL FAQ 回源。"""

import hashlib
import json
import re
from dataclasses import asdict

from redis.asyncio import Redis
from redis.exceptions import RedisError

from kb_manage_platform.domain.models import AnswerResult, RetrievedCandidate, UserContext
from kb_manage_platform.domain.ports import FaqCachePort


class RedisFaqCache:
    """Redis FAQ 缓存适配器，未命中时回源 MySQL。"""

    # 作用：保存 Redis、MySQL FAQ 仓储和缓存 TTL。
    def __init__(self, client: Redis, fallback: FaqCachePort, ttl_seconds: int) -> None:
        self._client = client
        self._fallback = fallback
        self._ttl_seconds = ttl_seconds

    # 作用：先读 Redis，未命中再读 MySQL 并回填缓存。
    async def lookup(self, question: str, user: UserContext) -> AnswerResult | None:
        """返回有权限访问的 FAQ 答案。"""
        key = self._cache_key(question, user)
        try:
            cached = await self._client.get(key)
            if cached:
                return self._deserialize(cached)
        except (RedisError, OSError):
            pass
        answer = await self._fallback.lookup(question, user)
        if answer:
            try:
                await self._client.set(key, self._serialize(answer), ex=self._ttl_seconds)
            except (RedisError, OSError):
                pass
        return answer

    # 作用：写入 MySQL 事实并将答案放入 Redis。
    async def save(self, question: str, answer: AnswerResult) -> None:
        """保存 FAQ 答案。"""
        await self._fallback.save(question, answer)

    # 作用：发布、更新、停用 FAQ 或权限变化时清理相关问题缓存。
    async def invalidate_question(self, question: str) -> None:
        """删除所有用户维度的问题缓存。"""
        normalized = re.sub(r"\s+", " ", question.strip().casefold())
        question_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        try:
            async for key in self._client.scan_iter(match=f"faq:answer:{question_hash}:*"):
                await self._client.delete(key)
        except (RedisError, OSError):
            return
    # 作用：生成包含用户权限边界的缓存键。
    def _cache_key(self, question: str, user: UserContext) -> str:
        """返回缓存键。"""
        normalized = re.sub(r"\s+", " ", question.strip().casefold())
        question_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        role_hash = hashlib.sha256("|".join(sorted(user.role_ids)).encode("utf-8")).hexdigest()[:12]
        return f"faq:answer:{question_hash}:{user.user_id}:{user.department_id}:{role_hash}:{user.permission_version}"

    # 作用：序列化 AnswerResult。
    @staticmethod
    def _serialize(answer: AnswerResult) -> str:
        """转换为 JSON。"""
        return json.dumps(asdict(answer), ensure_ascii=False)

    # 作用：反序列化 AnswerResult。
    @staticmethod
    def _deserialize(value: str | bytes) -> AnswerResult:
        """从 JSON 恢复答案。"""
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        data = json.loads(value)
        citations = tuple(RetrievedCandidate(**item) for item in data.get("citations", []))
        return AnswerResult(
            answer=str(data.get("answer", "")),
            citations=citations,
            warnings=tuple(data.get("warnings", [])),
        )