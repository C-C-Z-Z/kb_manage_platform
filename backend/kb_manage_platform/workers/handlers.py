"""注册 MySQL 后台任务处理器。"""

from collections.abc import Mapping

from kb_manage_platform.domain.models import JobRecord
from kb_manage_platform.services.faq_gap_service import FaqGapService
from kb_manage_platform.services.import_service import ImportService
from kb_manage_platform.workers.base import JobHandler
from kb_manage_platform.workers.job_types import (
    FAQ_MINING_JOB_TYPE,
    GAP_DETECTION_JOB_TYPE,
    INGEST_DOCUMENT_JOB_TYPE,
)

_DEFAULT_WINDOW_DAYS = 30
_MIN_WINDOW_DAYS = 1
_MAX_WINDOW_DAYS = 365


# 作用：从任务载荷读取合法分析窗口，异常时回退到配置默认值。
def _window_days(payload: Mapping[str, object], default: int) -> int:
    try:
        value = int(payload.get("window_days", default))
    except (TypeError, ValueError):
        return default
    if _MIN_WINDOW_DAYS <= value <= _MAX_WINDOW_DAYS:
        return value
    return default


class IngestionJobHandler(JobHandler):
    """文档入库任务处理器。"""

    job_type = INGEST_DOCUMENT_JOB_TYPE

    # 作用：保存入库服务。
    def __init__(self, service: ImportService) -> None:
        self._service = service

    # 作用：执行文档入库 LangGraph。
    async def handle(self, job: JobRecord) -> None:
        """处理入库任务。"""
        await self._service.execute(job)


class FaqMiningJobHandler(JobHandler):
    """周期执行 FAQ 挖掘的任务处理器。"""

    job_type = FAQ_MINING_JOB_TYPE

    # 作用：保存 FAQ/缺口服务和系统操作者身份。
    def __init__(
        self,
        service: FaqGapService,
        operator_id: str,
        default_window_days: int = _DEFAULT_WINDOW_DAYS,
    ) -> None:
        self._service = service
        self._operator_id = operator_id
        self._default_window_days = default_window_days

    # 作用：执行 FAQ 挖掘。
    async def handle(self, job: JobRecord) -> None:
        """使用任务载荷中的分析窗口执行挖掘。"""
        await self._service.mine_faq(
            self._operator_id,
            _window_days(job.payload, self._default_window_days),
        )


class GapDetectionJobHandler(JobHandler):
    """周期执行知识缺口检测的任务处理器。"""

    job_type = GAP_DETECTION_JOB_TYPE

    # 作用：保存 FAQ/缺口服务和系统操作者身份。
    def __init__(
        self,
        service: FaqGapService,
        operator_id: str,
        default_window_days: int = _DEFAULT_WINDOW_DAYS,
    ) -> None:
        self._service = service
        self._operator_id = operator_id
        self._default_window_days = default_window_days

    # 作用：执行知识缺口检测。
    async def handle(self, job: JobRecord) -> None:
        """使用任务载荷中的分析窗口执行缺口检测。"""
        await self._service.detect_gaps(
            self._operator_id,
            _window_days(job.payload, self._default_window_days),
        )