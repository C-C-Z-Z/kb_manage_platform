"""提供 MySQL 任务 Worker 和周期调度器的启动入口。"""

import asyncio

from kb_manage_platform.bootstrap.container import build_container
from kb_manage_platform.common.logger import logger
from kb_manage_platform.bootstrap.settings import Settings, get_settings
from kb_manage_platform.workers.handlers import (
    FaqMiningJobHandler,
    GapDetectionJobHandler,
    IngestionJobHandler,
)
from kb_manage_platform.workers.job_types import (
    FAQ_MINING_JOB_TYPE,
    GAP_DETECTION_JOB_TYPE,
    INGEST_DOCUMENT_JOB_TYPE,
)
from kb_manage_platform.workers.mysql_worker import MysqlJobWorker
from kb_manage_platform.workers.scheduler import MysqlJobScheduler, ScheduledJob


class WorkerApplication:
    """Worker 进程入口类。"""

    # 作用：创建 Worker、周期调度器和任务处理器。
    def __init__(self) -> None:
        settings = get_settings()
        self._container = build_container(settings)
        self._handlers = {
            INGEST_DOCUMENT_JOB_TYPE: IngestionJobHandler(self._container.import_service),
            FAQ_MINING_JOB_TYPE: FaqMiningJobHandler(
                self._container.faq_gap_service,
                settings.scheduler_operator_id,
                settings.scheduler_faq_mining_window_days,
            ),
            GAP_DETECTION_JOB_TYPE: GapDetectionJobHandler(
                self._container.faq_gap_service,
                settings.scheduler_operator_id,
                settings.scheduler_gap_detection_window_days,
            ),
        }
        self._worker = MysqlJobWorker(
            repository=self._container.job_repository,
            handlers=self._handlers,
            poll_interval_seconds=settings.mysql_job_poll_interval_seconds,
            batch_size=settings.mysql_job_batch_size,
            lock_timeout_seconds=settings.mysql_job_lock_timeout_seconds,
        )
        self._scheduler = MysqlJobScheduler(
            repository=self._container.job_repository,
            poll_interval_seconds=settings.scheduler_poll_interval_seconds,
            scheduled_jobs=self._build_scheduled_jobs(settings),
        )
        self._scheduler_enabled = settings.scheduler_enabled
        self._model_config_refresh_interval_seconds = max(
            1,
            settings.model_config_refresh_interval_seconds,
        )

    # 作用：根据配置构造 FAQ 挖掘和缺口检测周期任务。
    @staticmethod
    def _build_scheduled_jobs(settings: Settings) -> tuple[ScheduledJob, ...]:
        scheduled_jobs: list[ScheduledJob] = []
        if settings.scheduler_faq_mining_interval_seconds > 0:
            scheduled_jobs.append(
                ScheduledJob(
                    schedule_id="faq-mining",
                    job_type=FAQ_MINING_JOB_TYPE,
                    interval_seconds=settings.scheduler_faq_mining_interval_seconds,
                    payload={"window_days": settings.scheduler_faq_mining_window_days},
                )
            )
        if settings.scheduler_gap_detection_interval_seconds > 0:
            scheduled_jobs.append(
                ScheduledJob(
                    schedule_id="gap-detection",
                    job_type=GAP_DETECTION_JOB_TYPE,
                    interval_seconds=settings.scheduler_gap_detection_interval_seconds,
                    payload={"window_days": settings.scheduler_gap_detection_window_days},
                )
            )
        return tuple(scheduled_jobs)

    # 作用：定期加载数据库中的模型配置，使 Worker 跨进程同步管理端变更。
    async def _refresh_model_runtime(self) -> None:
        while True:
            await asyncio.sleep(self._model_config_refresh_interval_seconds)
            try:
                await self._container.configuration_service.initialize_runtime()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("model runtime refresh failed")

    # 作用：并发运行任务消费者、模型配置刷新器和周期调度器。
    async def run(self) -> None:
        """运行 Worker，直到进程收到取消信号。"""
        try:
            await self._container.configuration_service.initialize_runtime()
            async with asyncio.TaskGroup() as tasks:
                tasks.create_task(self._worker.run(), name="mysql-job-worker")
                tasks.create_task(self._refresh_model_runtime(), name="model-runtime-refresher")
                if self._scheduler_enabled:
                    tasks.create_task(self._scheduler.run(), name="mysql-job-scheduler")
        finally:
            await self._container.close()


# 作用：支持通过 python -m kb_manage_platform.workers.main 启动 Worker。
if __name__ == "__main__":
    asyncio.run(WorkerApplication().run())