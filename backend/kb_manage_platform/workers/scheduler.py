"""基于 MySQL 任务表的轻量周期调度器。"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from kb_manage_platform.common.logger import logger
from kb_manage_platform.domain.ports import JobRepositoryPort


@dataclass(frozen=True, slots=True)
class ScheduledJob:
    """描述一个需要周期投递到 MySQL 任务表的计划任务。"""

    schedule_id: str
    job_type: str
    interval_seconds: int
    payload: dict[str, object] = field(default_factory=dict)

    # 作用：校验周期任务定义，尽早暴露错误配置。
    def __post_init__(self) -> None:
        if not self.schedule_id.strip():
            raise ValueError("schedule_id must not be empty")
        if not self.job_type.strip():
            raise ValueError("job_type must not be empty")
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")


class MysqlJobScheduler:
    """周期向 MySQL 任务表投递计划任务。"""

    # 作用：保存任务仓储、轮询间隔和计划任务定义。
    def __init__(
        self,
        repository: JobRepositoryPort,
        poll_interval_seconds: int,
        scheduled_jobs: Sequence[ScheduledJob] = (),
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        self._repository = repository
        self._poll_interval_seconds = poll_interval_seconds
        self._scheduled_jobs = tuple(scheduled_jobs)
        self._running = False

    # 作用：投递当前时间片内到期的周期任务。
    async def enqueue_due(self, now: datetime | None = None) -> tuple[str, ...]:
        """按时间片和计划 ID 生成幂等键，同一周期只投递一次。"""
        scheduled_at = now or datetime.now(UTC)
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=UTC)
        job_ids: list[str] = []
        for scheduled_job in self._scheduled_jobs:
            slot = int(scheduled_at.timestamp()) // scheduled_job.interval_seconds
            idempotency_key = f"scheduled:{scheduled_job.schedule_id}:{slot}"
            try:
                job_id = await self._repository.enqueue(
                    scheduled_job.job_type,
                    dict(scheduled_job.payload),
                    idempotency_key,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "scheduled job enqueue failed: %s",
                    scheduled_job.schedule_id,
                )
                continue
            job_ids.append(job_id)
        return tuple(job_ids)

    # 作用：启动调度循环。
    async def run(self) -> None:
        """启动时立即检查一次，之后按轮询间隔持续投递。"""
        self._running = True
        while self._running:
            await self.enqueue_due()
            await asyncio.sleep(self._poll_interval_seconds)

    # 作用：停止调度循环。
    def stop(self) -> None:
        """设置停止标志。"""
        self._running = False