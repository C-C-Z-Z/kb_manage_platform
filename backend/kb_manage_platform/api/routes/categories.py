"""知识分类字典路由。"""

from fastapi import APIRouter

from kb_manage_platform.api.dependencies import (
    CategoryServiceDep,
    KnowledgeCreateUserDep,
    KnowledgeReadUserDep,
    KnowledgeUpdateUserDep,
)
from kb_manage_platform.api.schemas.category import (
    CategoryResponse,
    CreateCategoryRequest,
    UpdateCategoryRequest,
)

router = APIRouter(prefix="/knowledge-categories", tags=["knowledge-categories"])


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    _: KnowledgeReadUserDep,
    service: CategoryServiceDep,
) -> list[CategoryResponse]:
    """返回全部知识分类。"""
    return [CategoryResponse.from_domain(item) for item in await service.list_all()]


@router.post("", response_model=CategoryResponse)
async def create_category(
    payload: CreateCategoryRequest,
    user: KnowledgeCreateUserDep,
    service: CategoryServiceDep,
) -> CategoryResponse:
    """创建知识分类。"""
    item = await service.create(
        payload.category_id,
        payload.name,
        payload.description,
        payload.sort_order,
        user.user_id,
    )
    return CategoryResponse.from_domain(item)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    payload: UpdateCategoryRequest,
    user: KnowledgeUpdateUserDep,
    service: CategoryServiceDep,
) -> CategoryResponse:
    """更新知识分类。"""
    item = await service.update(
        category_id,
        payload.name,
        payload.description,
        payload.status,
        payload.sort_order,
        user.user_id,
    )
    return CategoryResponse.from_domain(item)


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    user: KnowledgeUpdateUserDep,
    service: CategoryServiceDep,
) -> None:
    """删除未被知识引用的分类。"""
    await service.delete(category_id, user.user_id)