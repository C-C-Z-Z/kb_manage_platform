"""使用 SQLAlchemy 持久化问答审计事件。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.domain.models import AuditRecord
from kb_manage_platform.infrastructure.mysql.models import QaAuditModel


class MysqlAuditLogger:
    """MySQL 问答审计适配器。"""

    # 作用：保存异步会话工厂。
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：分页查询审计事件。
    async def list_events(
        self,
        event_type: str,
        user_id: str,
        start_at,
        end_at,
        page: int,
        page_size: int,
    ) -> tuple[tuple[AuditRecord, ...], int]:
        """按过滤条件返回审计事件页。"""
        conditions = []
        if event_type.strip():
            conditions.append(QaAuditModel.event_type == event_type.strip())
        if user_id.strip():
            conditions.append(QaAuditModel.user_id == user_id.strip())
        if start_at is not None:
            conditions.append(QaAuditModel.created_at >= start_at)
        if end_at is not None:
            conditions.append(QaAuditModel.created_at <= end_at)
        async with self._session_factory() as session:
            count_stmt = select(func.count()).select_from(QaAuditModel)
            list_stmt = select(QaAuditModel)
            if conditions:
                count_stmt = count_stmt.where(*conditions)
                list_stmt = list_stmt.where(*conditions)
            total = int(await session.scalar(count_stmt) or 0)
            rows = (
                await session.scalars(
                    list_stmt.order_by(QaAuditModel.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        return (
            tuple(
                AuditRecord(
                    event_id=row.id,
                    event_type=row.event_type,
                    request_id=row.request_id,
                    user_id=row.user_id,
                    payload=dict(row.payload or {}),
                    created_at=row.created_at,
                )
                for row in rows
            ),
            total,
        )

    # 作用：写入问答或任务审计事件。
    async def record(self, event_type: str, payload: dict[str, object]) -> None:
        """写入 qa_audit 表。"""
        async with self._session_factory() as session:
            session.add(
                QaAuditModel(
                    event_type=event_type,
                    request_id=str(payload.get("request_id", "")),
                    user_id=str(payload.get("user_id", "")),
                    payload=dict(payload),
                )
            )
            await session.commit()