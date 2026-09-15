"""运营看板路由。"""

from datetime import datetime

from fastapi import APIRouter

from kb_manage_platform.api.dependencies import DashboardServiceDep, DashboardUserDep
from kb_manage_platform.api.schemas.dashboard import (
    DashboardOverviewResponse,
    TopItemResponse,
    TrendPointResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
async def dashboard_overview(
    _: DashboardUserDep,
    service: DashboardServiceDep,
    range_days: int = 7,
    start_at: str = "",
    end_at: str = "",
    department_id: str = "",
) -> DashboardOverviewResponse:
    """返回运营看板实时指标。"""
    parsed_start = datetime.fromisoformat(start_at) if start_at else None
    parsed_end = datetime.fromisoformat(end_at) if end_at else None
    data = await service.overview(
        range_days, parsed_start, parsed_end, department_id
    )
    return DashboardOverviewResponse(
        range_days=data.range_days,
        pv=data.pv,
        uv=data.uv,
        knowledge_count=data.knowledge_count,
        published_count=data.published_count,
        top_questions=[TopItemResponse(label=item.label, value=item.value) for item in data.top_questions],
        hot_knowledge=[TopItemResponse(label=item.label, value=item.value) for item in data.hot_knowledge],
        token_total=data.token_total,
        avg_latency_ms=data.avg_latency_ms,
        faq_hit_rate=data.faq_hit_rate,
        coverage_rate=data.coverage_rate,
        token_trend=[TrendPointResponse(label=item.label, value=item.value) for item in data.token_trend],
        latency_trend=[TrendPointResponse(label=item.label, value=item.value) for item in data.latency_trend],
    )
