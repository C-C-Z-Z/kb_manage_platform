"""实现 Redis 权限版本递增和缓存失效。"""

from redis.asyncio import Redis


class RedisPermissionVersionStore:
    """使用 Redis 保存权限版本并清理权限缓存。"""

    # 作用：保存 Redis 异步客户端。
    def __init__(self, client: Redis) -> None:
        self._client = client

    # 作用：递增权限版本并删除知识权限缓存。
    async def invalidate(
        self, knowledge_id: str, affected_user_ids: tuple[str, ...] = ()
    ) -> int:
        """返回新的全局权限版本。"""
        global_version = await self._client.incr("permission:version")
        await self._client.set(f"permission:knowledge:{knowledge_id}:version", global_version)
        await self._client.delete(f"permission:knowledge:{knowledge_id}:grants")
        for user_id in affected_user_ids:
            await self._client.delete(f"permission:user:{user_id}:snapshot")
        return int(global_version)