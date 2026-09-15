"""FAQ 与知识缺口闭环路由。"""

from fastapi import APIRouter

from kb_manage_platform.api.dependencies import (
    FaqGapServiceDep,
    FaqManageUserDep,
    GapManageUserDep,
)
from kb_manage_platform.api.schemas.faq_gap import (
    ConvertGapRequest,
    DetectGapRequest,
    FaqGapActionResponse,
    FaqStatusRequest,
    MineFaqRequest,
    ResolveGapRequest,
    ReviewFaqRequest,
    UpdateFaqRequest,
)
from kb_manage_platform.domain.models import PermissionGrant, PermissionScope

router = APIRouter(tags=["faq-gap"])


def _response(result) -> FaqGapActionResponse:
    """转换流程结果。"""
    return FaqGapActionResponse(
        action=result.action.value,
        processed_count=result.processed_count,
        candidate_ids=list(result.candidate_ids),
        gap_ids=list(result.gap_ids),
        draft_id=result.draft_id,
    )


@router.post("/faq/mine", response_model=FaqGapActionResponse)
async def mine_faq(
    payload: MineFaqRequest,
    user: FaqManageUserDep,
    service: FaqGapServiceDep,
) -> FaqGapActionResponse:
    """执行 FAQ 聚类。"""
    return _response(await service.mine_faq(user.user_id, payload.window_days))


@router.get("/faq/candidates")
async def list_faq_candidates(_: FaqManageUserDep, service: FaqGapServiceDep):
    """返回 FAQ 候选列表。"""
    candidates = await service.list_candidates()
    return {
        "items": [
            {
                "candidate_id": item.candidate_id,
                "question": item.representative_question,
                "answer": item.standard_answer,
                "frequency": item.frequency,
                "distinct_users": item.distinct_users,
                "status": item.status.value,
                "permission_signature": item.permission_signature,
                "confidence": item.confidence,
            }
            for item in candidates
        ]
    }


@router.post("/faq/review", response_model=FaqGapActionResponse)
async def review_faq(
    payload: ReviewFaqRequest,
    user: FaqManageUserDep,
    service: FaqGapServiceDep,
) -> FaqGapActionResponse:
    """审核并发布或驳回 FAQ。"""
    grants = tuple(
        PermissionGrant(PermissionScope(item.scope), item.subject_id, item.include_descendants)
        for item in payload.grants
    )
    result = await service.review_faq(
        payload.candidate_id,
        payload.question,
        payload.decision,
        user.user_id,
        grants,
        payload.reason,
    )
    return _response(result)


@router.get("/faq/published")
async def list_published_faqs(_: FaqManageUserDep, service: FaqGapServiceDep):
    """返回已发布 FAQ 管理列表。"""
    items = await service.list_published_faqs()
    return {
        "items": [
            {
                "faq_id": item.faq_id,
                "question": item.standard_question,
                "answer": item.answer_text,
                "status": item.status,
                "knowledge_id": item.knowledge_id,
                "version_id": item.version_id,
                "updated_at": item.updated_at.isoformat() if item.updated_at else "",
            }
            for item in items
        ]
    }


@router.put("/faq/{faq_id}")
async def update_published_faq(
    faq_id: str,
    payload: UpdateFaqRequest,
    user: FaqManageUserDep,
    service: FaqGapServiceDep,
):
    """更新已发布 FAQ。"""
    item = await service.update_published_faq(
        faq_id, payload.question, payload.answer, user.user_id
    )
    return {
        "faq_id": item.faq_id,
        "question": item.standard_question,
        "answer": item.answer_text,
        "status": item.status,
    }


@router.post("/faq/{faq_id}/status")
async def set_published_faq_status(
    faq_id: str,
    payload: FaqStatusRequest,
    user: FaqManageUserDep,
    service: FaqGapServiceDep,
):
    """启用或停用 FAQ。"""
    item = await service.set_published_faq_status(faq_id, payload.status, user.user_id)
    return {"faq_id": item.faq_id, "status": item.status}


@router.post("/gaps/detect", response_model=FaqGapActionResponse)
async def detect_gaps(
    payload: DetectGapRequest,
    user: GapManageUserDep,
    service: FaqGapServiceDep,
) -> FaqGapActionResponse:
    """执行知识缺口检测。"""
    return _response(await service.detect_gaps(user.user_id, payload.window_days))


@router.get("/gaps")
async def list_gaps(_: GapManageUserDep, service: FaqGapServiceDep):
    """返回知识缺口列表。"""
    gaps = await service.list_gaps()
    return {
        "items": [
            {
                "gap_id": item.gap_id,
                "question": item.representative_question,
                "gap_type": item.gap_type.value,
                "status": item.status.value,
                "frequency": item.frequency,
                "departments": list(item.department_ids),
                "max_similarity": item.max_similarity,
                "suggested_category": item.suggested_category,
            }
            for item in gaps
        ]
    }


@router.post("/gaps/{gap_id}/convert", response_model=FaqGapActionResponse)
async def convert_gap(
    gap_id: str,
    payload: ConvertGapRequest,
    user: GapManageUserDep,
    service: FaqGapServiceDep,
) -> FaqGapActionResponse:
    """创建知识补充草稿。"""
    return _response(
        await service.convert_gap(gap_id, payload.title, payload.category_id, user.user_id)
    )


@router.post("/gaps/{gap_id}/status", response_model=FaqGapActionResponse)
async def update_gap_status(
    gap_id: str,
    payload: ResolveGapRequest,
    user: GapManageUserDep,
    service: FaqGapServiceDep,
) -> FaqGapActionResponse:
    """更新缺口状态。"""
    return _response(
        await service.resolve_gap(gap_id, user.user_id, payload.decision, payload.reason)
    )
