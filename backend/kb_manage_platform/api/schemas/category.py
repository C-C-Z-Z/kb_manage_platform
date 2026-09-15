"""知识分类 API 模型。"""

from pydantic import BaseModel, Field

from kb_manage_platform.domain.models import KnowledgeCategory


class CategoryResponse(BaseModel):
    category_id: str
    name: str
    description: str
    status: str
    sort_order: int

    @classmethod
    def from_domain(cls, item: KnowledgeCategory) -> "CategoryResponse":
        return cls(
            category_id=item.category_id,
            name=item.name,
            description=item.description,
            status=item.status,
            sort_order=item.sort_order,
        )


class CreateCategoryRequest(BaseModel):
    category_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    sort_order: int = 0


class UpdateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    status: str = Field(default="active", pattern="^(active|disabled)$")
    sort_order: int = 0