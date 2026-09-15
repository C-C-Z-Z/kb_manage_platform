"""实现运营看板的 MySQL 聚合查询。"""

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.domain.models import (
    DashboardOverview,
    DashboardTopItem,
    DashboardTrendPoint,
)
from kb_manage_platform.infrastructure.mysql.models import (
    UserModel,
    KnowledgeUnitModel,
    QaAuditModel,
    QaCitationModel,
    QaMessageModel,
)


class MysqlDashboardRepository:
    """按时间窗口实时聚合核心运营指标。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def overview(
        self,
        range_days: int,
        start_at=None,
        end_at=None,
        department_id: str = "",
    ) -> DashboardOverview:
        """返回指定时间范围和部门的实时运营指标。"""
        now = datetime.now(UTC)
        days = max(1, min(range_days, 90))
        cutoff = start_at or (now - timedelta(days=days))
        upper_bound = end_at or now
        audit_stmt = select(QaAuditModel).where(
            QaAuditModel.created_at >= cutoff,
            QaAuditModel.created_at <= upper_bound,
        )
        if department_id.strip():
            audit_stmt = audit_stmt.join(
                UserModel, UserModel.user_id == QaAuditModel.user_id
            ).where(UserModel.department_id == department_id.strip())
        async with self._session_factory() as session:
            audits = (
                await session.scalars(
                    audit_stmt.order_by(QaAuditModel.created_at.asc())
                )
            ).all()
            knowledge_count = int(
                await session.scalar(select(func.count()).select_from(KnowledgeUnitModel)) or 0
            )
            published_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(KnowledgeUnitModel)
                    .where(KnowledgeUnitModel.status == "published")
                )
                or 0
            )
            citation_stmt = (
                select(QaCitationModel.knowledge_id, func.count())
                .join(QaMessageModel, QaMessageModel.message_id == QaCitationModel.message_id)
                .where(
                    QaMessageModel.created_at >= cutoff,
                    QaMessageModel.created_at <= upper_bound,
                )
            )
            if department_id.strip():
                citation_stmt = citation_stmt.join(
                    UserModel, UserModel.user_id == QaMessageModel.user_id
                ).where(UserModel.department_id == department_id.strip())
            citation_rows = (
                await session.execute(
                    citation_stmt
                    .group_by(QaCitationModel.knowledge_id)
                    .order_by(func.count().desc())
                    .limit(5)
                )
            ).all()

        completed = [row for row in audits if row.event_type == "qa.completed"]
        metrics = [row for row in audits if row.event_type == "qa.metrics"]
        faq_hit_count = sum(1 for row in completed if bool(row.payload.get("faq_hit")))
        coverage_count = sum(1 for row in completed if int(row.payload.get("authorized_count", 0) or 0) > 0)
        question_counter = Counter(
            str(row.payload.get("question", "")).strip()
            for row in completed
            if str(row.payload.get("question", "")).strip()
        )
        token_by_day: dict[date, int] = defaultdict(int)
        latency_by_day: dict[date, list[float]] = defaultdict(list)
        token_total = 0
        latency_values: list[float] = []
        for row in metrics:
            day = row.created_at.date()
            token_count = int(row.payload.get("estimated_tokens", 0) or 0)
            latency = float(row.payload.get("latency_ms", 0.0) or 0.0)
            token_by_day[day] += token_count
            latency_by_day[day].append(latency)
            token_total += token_count
            latency_values.append(latency)

        start_day = (upper_bound - timedelta(days=days - 1)).date()
        day_keys = [start_day + timedelta(days=offset) for offset in range(days)]
        token_trend = tuple(
            DashboardTrendPoint(day.isoformat(), float(token_by_day[day])) for day in day_keys
        )
        latency_trend = tuple(
            DashboardTrendPoint(
                day.isoformat(),
                round(sum(latency_by_day[day]) / len(latency_by_day[day]), 2)
                if latency_by_day[day]
                else 0.0,
            )
            for day in day_keys
        )
        return DashboardOverview(
            range_days=days,
            pv=len(completed),
            uv=len({row.user_id for row in completed}),
            knowledge_count=knowledge_count,
            published_count=published_count,
            top_questions=tuple(
                DashboardTopItem(label, float(count)) for label, count in question_counter.most_common(5)
            ),
            hot_knowledge=tuple(
                DashboardTopItem(str(knowledge_id), float(count))
                for knowledge_id, count in citation_rows
            ),
            token_total=token_total,
            avg_latency_ms=round(sum(latency_values) / len(latency_values), 2)
            if latency_values
            else 0.0,
            faq_hit_rate=round(faq_hit_count / len(completed), 4) if completed else 0.0,
            coverage_rate=round(coverage_count / len(completed), 4) if completed else 0.0,
            token_trend=token_trend,
            latency_trend=latency_trend,
        )
