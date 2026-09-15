"""运营看板应用服务。"""

from kb_manage_platform.domain.models import DashboardOverview
from kb_manage_platform.domain.ports import DashboardRepositoryPort


class DashboardService:
    """读取实时运营聚合指标。"""

    def __init__(self, repository: DashboardRepositoryPort) -> None:
        self._repository = repository

    async def overview(
        self,
        range_days: int,
        start_at=None,
        end_at=None,
        department_id: str = "",
    ) -> DashboardOverview:
        """返回指定时间范围和部门的看板数据。"""
        return await self._repository.overview(
            range_days, start_at, end_at, department_id
        )
