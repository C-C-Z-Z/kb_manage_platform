"""实现基于 MySQL 任务表的轮询 Worker。"""

import asyncio
from collections.abc import Mapping
from uuid import uuid4

from kb_manage_platform.domain.ports import JobRepositoryPort
from kb_manage_platform.common.logger import logger
from kb_manage_platform.workers.base import JobHandler


class MysqlJobWorker:
    """不使用 Celery 和 RabbitMQ 的 MySQL 任务 Worker。"""

    # 作用：保存任务仓储、处理器和轮询参数。
    def __init__(
        self,
        repository: JobRepositoryPort,
        handlers: Mapping[str, JobHandler],
        poll_interval_seconds: int,
        batch_size: int,
        lock_timeout_seconds: int,
    ) -> None:
        self._repository = repository
        self._handlers = dict(handlers)
        self._poll_interval_seconds = poll_interval_seconds
        self._batch_size = batch_size
        self._lock_timeout_seconds = lock_timeout_seconds
        self._worker_id = str(uuid4())
        self._running = False

    # 作用：启动 Worker 循环。
    async def run(self) -> None:
        """持续领取并处理 MySQL 任务。"""
        self._running = True
        while self._running:
            try:
                processed = await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("job polling failed")
                processed = 0
            if processed == 0:
                await asyncio.sleep(self._poll_interval_seconds)

    # 作用：停止 Worker 循环。
    def stop(self) -> None:
        """设置停止标志。"""
        self._running = False

    # 作用：领取一批任务并逐个执行。
    async def poll_once(self) -> int:
        """返回本次处理任务数量。"""
        await self._repository.release_stale(self._lock_timeout_seconds)
        jobs = await self._repository.claim_batch(self._worker_id, self._batch_size)
        for job in jobs:
            await self._execute(job)
        return len(jobs)

    # 作用：执行单个任务并更新成功或失败状态。
    async def _execute(self, job) -> None:
        """执行任务并处理重试。"""
        handler = self._handlers.get(job.job_type)
        if handler is None:
            await self._repository.mark_failed(job.job_id, "handler not found", retry=False)
            return
        try:
            await handler.handle(job)
            await self._repository.mark_succeeded(job.job_id)
        except Exception as exc:
            logger.exception("job failed: %s", job.job_id)
            retry = job.attempts + 1 < job.max_attempts
            await self._repository.mark_failed(job.job_id, str(exc), retry)