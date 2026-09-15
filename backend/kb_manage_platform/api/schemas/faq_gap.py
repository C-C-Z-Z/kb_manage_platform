"""FAQ 与知识缺口 API 模型。"""

from pydantic import BaseModel, Field

from kb_manage_platform.api.schemas.knowledge import PermissionGrantSchema


class MineFaqRequest(BaseModel):
    """FAQ 挖掘请求。"""

    window_days: int = Field(default=30, ge=1, le=365, description="分析窗口天数")


class ReviewFaqRequest(BaseModel):
    """FAQ 审核请求。"""

    candidate_id: str = Field(..., description="候选 FAQ ID")
    question: str = Field(..., description="标准问题")
    decision: str = Field(..., description="approve 或 reject")
    grants: list[PermissionGrantSchema] = Field(default_factory=list, description="FAQ 权限")
    reason: str = Field(default="", description="驳回原因")


class UpdateFaqRequest(BaseModel):
    """已发布 FAQ 内容更新请求。"""

    question: str = Field(..., min_length=1, description="标准问题")
    answer: str = Field(..., min_length=1, description="标准答案")


class FaqStatusRequest(BaseModel):
    """FAQ 启停请求。"""

    status: str = Field(..., pattern="^(published|disabled)$", description="published 或 disabled")


class DetectGapRequest(BaseModel):
    """知识缺口识别请求。"""

    window_days: int = Field(default=30, ge=1, le=365, description="分析窗口天数")


class ConvertGapRequest(BaseModel):
    """缺口转建知识补充草稿请求。"""

    title: str = Field(..., description="补充知识标题")
    category_id: str = Field(default="", description="建议分类")


class ResolveGapRequest(BaseModel):
    """缺口解决或忽略请求。"""

    decision: str = Field(default="resolve", description="resolve 或 ignore")
    reason: str = Field(default="", description="处理说明")


class FaqGapActionResponse(BaseModel):
    """FAQ/缺口动作响应。"""

    action: str
    processed_count: int
    candidate_ids: list[str] = Field(default_factory=list)
    gap_ids: list[str] = Field(default_factory=list)
    draft_id: str = ""
