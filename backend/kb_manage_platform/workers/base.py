"""定义 MySQL 任务 Worker 的处理器基类。"""

from abc import ABC, abstractmethod

from kb_manage_platform.domain.models import JobRecord


class JobHandler(ABC):
    """后台任务处理器基类。"""

    job_type = "base"

    # 作用：执行指定类型的后台任务。
    @abstractmethod
    async def handle(self, job: JobRecord) -> None:
        """处理任务。"""
        raise NotImplementedError