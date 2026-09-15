"""提供审计日志查询应用服务。"""

from datetime import datetime

from kb_manage_platform.domain.models import AuditRecord
from kb_manage_platform.domain.ports import AuditQueryPort


class AuditService:
    """读取审计日志。"""

    def __init__(self, repository: AuditQueryPort) -> None:
        self._repository = repository

    async def list_events(
        self,
        event_type: str,
        user_id: str,
        start_at: datetime | None,
        end_at: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[AuditRecord, ...], int]:
        """返回审计事件页。"""
        return await self._repository.list_events(
            event_type, user_id, start_at, end_at, page, page_size
        )

    async def export_events(
        self,
        event_type: str,
        user_id: str,
        start_at: datetime | None,
        end_at: datetime | None,
    ) -> tuple[AuditRecord, ...]:
        """导出最多一万条审计事件。"""
        rows, _ = await self._repository.list_events(
            event_type, user_id, start_at, end_at, 1, 10000
        )
        return rows