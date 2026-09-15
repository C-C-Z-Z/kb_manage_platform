"""创建 MySQL 异步引擎和会话工厂。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class Database:
    """管理 MySQL 异步引擎生命周期。"""

    # 作用：创建异步引擎和会话工厂。
    def __init__(self, url: str, pool_size: int = 10, echo: bool = False) -> None:
        self.engine: AsyncEngine = create_async_engine(url, pool_size=pool_size, echo=echo)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    # 作用：提供一个自动提交和关闭的数据库会话。
    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """创建数据库会话。"""
        async with self.session_factory() as session:
            yield session

    # 作用：释放数据库连接池。
    async def dispose(self) -> None:
        """关闭数据库引擎。"""
        await self.engine.dispose()