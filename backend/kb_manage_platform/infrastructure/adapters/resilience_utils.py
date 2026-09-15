"""提供有上限的异步重试工具。"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class RetryPolicy:
    """对瞬时错误执行指数退避重试。"""

    # 作用：设置重试次数、基础延迟和最大延迟。
    def __init__(self, attempts: int = 3, base_delay: float = 0.2, max_delay: float = 3.0) -> None:
        self._attempts = max(1, attempts)
        self._base_delay = base_delay
        self._max_delay = max_delay

    # 作用：执行带有指数退避的操作。
    async def run(self, operation: Callable[[], Awaitable[T]]) -> T:
        """返回成功结果，超过次数后抛出最后一次异常。"""
        last_error: Exception | None = None
        for attempt in range(self._attempts):
            try:
                return await operation()
            except Exception as exc:
                last_error = exc
                if attempt + 1 >= self._attempts:
                    break
                delay = min(self._max_delay, self._base_delay * (2**attempt))
                delay += random.uniform(0, delay * 0.2)
                await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error
