"""验证 MySQL 任务仓储在提交后的对象转换安全性。"""

from datetime import UTC, datetime

import pytest

from kb_manage_platform.domain.models import JobStage, JobStatus
from kb_manage_platform.infrastructure.mysql.job_repository import MysqlJobRepository


class ExpiringJobRow:
    """模拟 SQLAlchemy 会话提交后属性过期的任务行。"""

    def __init__(self) -> None:
        self.job_id = "job-1"
        self.job_type = "faq.mining"
        self.payload = {"window_days": 30}
        self.status = JobStatus.PENDING.value
        self.priority = 0
        self.run_at = datetime.now(UTC)
        self.locked_by = None
        self.locked_at = None
        self.heartbeat_at = None
        self.attempts = 0
        self.max_attempts = 3
        self.progress = 0
        self.stage = JobStage.QUEUED.value
        self.idempotency_key = "scheduled:faq-mining:1"
        self.last_error = ""
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def expire(self) -> None:
        self.__dict__.clear()

    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"claim_batch accessed expired attribute: {name}")


class FakeScalarResult:
    def __init__(self, rows: list[ExpiringJobRow]) -> None:
        self._rows = rows

    def all(self) -> list[ExpiringJobRow]:
        return self._rows


class FakeSession:
    def __init__(self, rows: list[ExpiringJobRow]) -> None:
        self.rows = rows
        self.committed = False

    async def scalars(self, statement: object) -> FakeScalarResult:
        return FakeScalarResult(self.rows)

    async def commit(self) -> None:
        self.committed = True
        for row in self.rows:
            row.expire()


class FakeSessionContext:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> FakeSession:
        return self._session

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self) -> FakeSessionContext:
        return FakeSessionContext(self._session)


@pytest.mark.asyncio
async def test_claim_batch_converts_rows_before_commit_expires_them() -> None:
    session = FakeSession([ExpiringJobRow()])
    repository = MysqlJobRepository(FakeSessionFactory(session))  # type: ignore[arg-type]

    jobs = await repository.claim_batch("worker-1", 10)

    assert session.committed is True
    assert len(jobs) == 1
    assert jobs[0].job_id == "job-1"
    assert jobs[0].status is JobStatus.RUNNING
    assert jobs[0].attempts == 1
    assert jobs[0].payload == {"window_days": 30}