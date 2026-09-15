"""验证 FAQ 挖掘和知识缺口检测的周期调度行为。"""

from datetime import UTC, datetime, timedelta

import pytest

from kb_manage_platform.domain.models import JobRecord
from kb_manage_platform.workers.handlers import FaqMiningJobHandler, GapDetectionJobHandler
from kb_manage_platform.workers.job_types import FAQ_MINING_JOB_TYPE, GAP_DETECTION_JOB_TYPE
from kb_manage_platform.workers.scheduler import MysqlJobScheduler, ScheduledJob


class FakeJobRepository:
    """按幂等键去重的内存任务仓储。"""

    def __init__(self) -> None:
        self.enqueued: list[tuple[str, dict[str, object], str]] = []
        self._job_ids: dict[str, str] = {}

    async def enqueue(
        self,
        job_type: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> str:
        existing = self._job_ids.get(idempotency_key)
        if existing is not None:
            return existing
        job_id = f"job-{len(self.enqueued) + 1}"
        self._job_ids[idempotency_key] = job_id
        self.enqueued.append((job_type, dict(payload), idempotency_key))
        return job_id


class FakeFaqGapService:
    """记录周期处理器调用参数的测试服务。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    async def mine_faq(self, operator_id: str, window_days: int = 30) -> object:
        self.calls.append(("mine_faq", operator_id, window_days))
        return object()

    async def detect_gaps(self, operator_id: str, window_days: int = 30) -> object:
        self.calls.append(("detect_gaps", operator_id, window_days))
        return object()


@pytest.mark.asyncio
async def test_scheduler_enqueues_same_slot_once_and_next_slot_again() -> None:
    repository = FakeJobRepository()
    scheduler = MysqlJobScheduler(
        repository=repository,
        poll_interval_seconds=30,
        scheduled_jobs=(
            ScheduledJob(
                schedule_id="faq-mining",
                job_type=FAQ_MINING_JOB_TYPE,
                interval_seconds=3600,
                payload={"window_days": 30},
            ),
        ),
    )
    start = datetime(2026, 9, 14, 10, 0, tzinfo=UTC)

    first = await scheduler.enqueue_due(start)
    repeated = await scheduler.enqueue_due(start + timedelta(minutes=59))
    next_slot = await scheduler.enqueue_due(start + timedelta(hours=1))

    assert first == repeated == ("job-1",)
    assert next_slot == ("job-2",)
    first_slot = int(start.timestamp()) // 3600
    assert repository.enqueued == [
        (FAQ_MINING_JOB_TYPE, {"window_days": 30}, f"scheduled:faq-mining:{first_slot}"),
        (FAQ_MINING_JOB_TYPE, {"window_days": 30}, f"scheduled:faq-mining:{first_slot + 1}"),
    ]


@pytest.mark.asyncio
async def test_faq_mining_handler_uses_payload_window() -> None:
    service = FakeFaqGapService()
    handler = FaqMiningJobHandler(service, "system-scheduler", 30)

    await handler.handle(
        JobRecord(
            job_id="job-1",
            job_type=FAQ_MINING_JOB_TYPE,
            payload={"window_days": 14},
        )
    )

    assert service.calls == [("mine_faq", "system-scheduler", 14)]


@pytest.mark.asyncio
async def test_gap_detection_handler_falls_back_for_invalid_window() -> None:
    service = FakeFaqGapService()
    handler = GapDetectionJobHandler(service, "system-scheduler", 30)

    await handler.handle(
        JobRecord(
            job_id="job-2",
            job_type=GAP_DETECTION_JOB_TYPE,
            payload={"window_days": "invalid"},
        )
    )

    assert service.calls == [("detect_gaps", "system-scheduler", 30)]