"""实现基于 MinIO 的对象存储适配器。"""

import asyncio
from io import BytesIO

from minio import Minio


class MinioObjectStorage:
    """使用 MinIO 保存原始文档、Markdown 和抽取图片。"""

    # 作用：保存连接参数并延迟创建桶。
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False) -> None:
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._bucket_lock = asyncio.Lock()
        self._known_buckets: set[str] = set()

    # 作用：保存对象并返回对象键。
    async def put_bytes(
        self,
        bucket: str,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """写入对象存储。"""
        await self._ensure_bucket(bucket)
        await asyncio.to_thread(
            self._client.put_object,
            bucket,
            object_key,
            BytesIO(content),
            len(content),
            content_type=content_type or "application/octet-stream",
        )
        return object_key

    # 作用：读取指定桶中的对象内容。
    async def get_bytes(self, bucket: str, object_key: str) -> bytes:
        """读取对象存储中的二进制内容。"""
        response = await asyncio.to_thread(self._client.get_object, bucket, object_key)
        try:
            return await asyncio.to_thread(response.read)
        finally:
            response.close()
            response.release_conn()

    # 作用：删除单个对象。
    async def delete_object(self, bucket: str, object_key: str) -> None:
        """从对象存储删除指定对象。"""
        await asyncio.to_thread(self._client.remove_object, bucket, object_key)

    # 作用：删除指定前缀下的全部对象。
    async def delete_prefix(self, bucket: str, prefix: str) -> int:
        """递归删除前缀对象并返回删除数量。"""
        if not prefix:
            raise ValueError("object prefix must not be empty")
        objects = await asyncio.to_thread(
            lambda: list(self._client.list_objects(bucket, prefix=prefix, recursive=True))
        )
        for item in objects:
            await asyncio.to_thread(self._client.remove_object, bucket, item.object_name)
        return len(objects)

    # 作用：确保目标桶已经存在。
    async def _ensure_bucket(self, bucket: str) -> None:
        """幂等创建 MinIO 桶。"""
        async with self._bucket_lock:
            if bucket in self._known_buckets:
                return
            exists = await asyncio.to_thread(self._client.bucket_exists, bucket)
            if not exists:
                await asyncio.to_thread(self._client.make_bucket, bucket)
            self._known_buckets.add(bucket)