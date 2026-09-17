"""实现基于 MySQL 任务表的后台任务仓储。"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.infrastructure.mysql.models import BackgroundJobModel
from kb_manage_platform.domain.models import JobRecord, JobStage, JobStatus


class MysqlJobRepository:
    """MySQL 任务队列仓储，不使用 Celery 或 RabbitMQ。"""

    # 作用：保存异步会话工厂。
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：创建或复用幂等后台任务。
    async def enqueue(
        self, job_type: str, payload: dict[str, object], idempotency_key: str
    ) -> str:
        """写入 background_job 表并返回任务 ID。"""
        async with self._session_factory() as session:
            existing = await session.scalar(
                select(BackgroundJobModel).where(
                    BackgroundJobModel.idempotency_key == idempotency_key
                )
            )
            if existing:
                return existing.job_id
            job_id = str(uuid4())
            model = BackgroundJobModel(
                job_id=job_id,
                job_type=job_type,
                payload=dict(payload),
                status=JobStatus.PENDING.value,
                idempotency_key=idempotency_key,
            )
            session.add(model)
            await session.commit()
            return job_id

    # 作用：领取一批到期任务并标记为执行中。
    async def claim_batch(self, worker_id: str, batch_size: int) -> list[JobRecord]:
        """使用 SKIP LOCKED 防止多个 Worker 重复领取。"""
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(BackgroundJobModel)
                    .where(
                        BackgroundJobModel.status == JobStatus.PENDING.value,
                        BackgroundJobModel.run_at <= now,
                    )
                    .order_by(BackgroundJobModel.priority.desc(), BackgroundJobModel.run_at)
                    .with_for_update(skip_locked=True)
                    .limit(batch_size)
                )
            ).all()
            for row in rows:
                row.status = JobStatus.RUNNING.value
                row.locked_by = worker_id
                row.locked_at = now
                row.heartbeat_at = now
                row.attempts += 1
            records = [self._to_record(row) for row in rows]
            await session.commit()
            return records

    # 作用：按 ID 读取任务状态。
    async def get(self, job_id: str) -> JobRecord | None:
        """返回任务记录。"""
        async with self._session_factory() as session:
            model = await session.get(BackgroundJobModel, job_id)
            return self._to_record(model) if model else None

    # 作用：更新任务阶段和进度。
    async def update_progress(self, job_id: str, stage: str, progress: int) -> None:
        """写入任务阶段和进度。"""
        normalized_progress = max(0, min(100, int(progress)))
        async with self._session_factory() as session:
            model = await session.get(BackgroundJobModel, job_id)
            if model is None:
                return
            model.stage = stage
            model.progress = normalized_progress
            model.heartbeat_at = datetime.now(UTC)
            await session.commit()

    # 作用：仅刷新当前 Worker 仍然持有的运行中任务心跳。
    async def touch(self, job_id: str, worker_id: str) -> None:
        """更新任务心跳时间。"""
        async with self._session_factory() as session:
            await session.execute(
                update(BackgroundJobModel)
                .where(
                    BackgroundJobModel.job_id == job_id,
                    BackgroundJobModel.status == JobStatus.RUNNING.value,
                    BackgroundJobModel.locked_by == worker_id,
                )
                .values(heartbeat_at=datetime.now(UTC))
            )
            await session.commit()

    # 作用：将失败任务重新放入待处理队列。
    async def retry(self, job_id: str) -> None:
        """重置失败任务状态和尝试次数。"""
        async with self._session_factory() as session:
            model = await session.get(BackgroundJobModel, job_id)
            if model is None:
                raise LookupError(f"job not found: {job_id}")
            if model.status != JobStatus.FAILED.value:
                raise ValueError("only failed jobs can be retried")
            model.status = JobStatus.PENDING.value
            model.stage = JobStage.QUEUED.value
            model.progress = 0
            model.attempts = 0
            model.last_error = ""
            model.run_at = datetime.now(UTC)
            model.locked_by = None
            model.locked_at = None
            model.heartbeat_at = None
            await session.commit()

    # 作用：标记任务执行成功。
    async def mark_succeeded(self, job_id: str) -> None:
        """更新 background_job 状态。"""
        async with self._session_factory() as session:
            await session.execute(
                update(BackgroundJobModel)
                .where(BackgroundJobModel.job_id == job_id)
                .values(
                    status=JobStatus.SUCCEEDED.value,
                    locked_by=None,
                    locked_at=None,
                    heartbeat_at=None,
                    progress=100,
                    stage=JobStage.COMPLETED.value,
                )
            )
            await session.commit()

    # 作用：标记任务失败并安排重试。
    async def mark_failed(self, job_id: str, error: str, retry: bool) -> None:
        """按策略更新任务状态。"""
        async with self._session_factory() as session:
            model = await session.get(BackgroundJobModel, job_id)
            if model is None:
                return
            model.last_error = error[:2000]
            model.locked_by = None
            model.locked_at = None
            model.heartbeat_at = None
            if retry and model.attempts < model.max_attempts:
                model.status = JobStatus.PENDING.value
                model.stage = JobStage.QUEUED.value
                model.progress = 0
                model.run_at = datetime.now(UTC) + timedelta(seconds=2**model.attempts)
            else:
                model.status = JobStatus.FAILED.value
                model.stage = JobStage.FAILED.value
            await session.commit()

    # 作用：回收锁超时任务。
    async def release_stale(self, timeout_seconds: int) -> int:
        """将心跳超时任务重排，超过最大尝试次数时直接失败。"""
        now = datetime.now(UTC)
        deadline = now - timedelta(seconds=timeout_seconds)
        stale_conditions = (
            BackgroundJobModel.status == JobStatus.RUNNING.value,
            BackgroundJobModel.heartbeat_at < deadline,
        )
        async with self._session_factory() as session:
            failed_result = await session.execute(
                update(BackgroundJobModel)
                .where(
                    *stale_conditions,
                    BackgroundJobModel.attempts >= BackgroundJobModel.max_attempts,
                )
                .values(
                    status=JobStatus.FAILED.value,
                    stage=JobStage.FAILED.value,
                    locked_by=None,
                    locked_at=None,
                    heartbeat_at=None,
                    last_error="job lock timed out after max attempts",
                )
            )
            pending_result = await session.execute(
                update(BackgroundJobModel)
                .where(
                    *stale_conditions,
                    BackgroundJobModel.attempts < BackgroundJobModel.max_attempts,
                )
                .values(
                    status=JobStatus.PENDING.value,
                    stage=JobStage.QUEUED.value,
                    progress=0,
                    run_at=now,
                    locked_by=None,
                    locked_at=None,
                    heartbeat_at=None,
                )
            )
            await session.commit()
            return int(failed_result.rowcount or 0) + int(pending_result.rowcount or 0)  # type: ignore

    # 作用：将 ORM 任务转换为领域模型。
    @staticmethod
    def _to_record(model: BackgroundJobModel) -> JobRecord:
        """转换任务模型。"""
        return JobRecord(
            job_id=model.job_id,
            job_type=model.job_type,
            payload=dict(model.payload),
            status=JobStatus(model.status),
            attempts=model.attempts,
            max_attempts=model.max_attempts,
            idempotency_key=model.idempotency_key,
            progress=model.progress,
            stage=JobStage(model.stage),
            last_error=model.last_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

