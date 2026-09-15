"""运营看板 API 模型。"""

from pydantic import BaseModel, Field


class TopItemResponse(BaseModel):
    """排行榜条目。"""

    label: str
    value: float


class TrendPointResponse(BaseModel):
    """趋势点。"""

    label: str
    value: float


class DashboardOverviewResponse(BaseModel):
    """运营看板响应。"""

    range_days: int
    pv: int
    uv: int
    knowledge_count: int
    published_count: int
    top_questions: list[TopItemResponse] = Field(default_factory=list)
    hot_knowledge: list[TopItemResponse] = Field(default_factory=list)
    token_total: int
    avg_latency_ms: float
    faq_hit_rate: float
    coverage_rate: float
    token_trend: list[TrendPointResponse] = Field(default_factory=list)
    latency_trend: list[TrendPointResponse] = Field(default_factory=list)
