"""知识维护 API 的请求和响应模型。"""

from pydantic import BaseModel, Field

from kb_manage_platform.domain.models import (
    KnowledgeMaintenanceResult,
    KnowledgePermissionSet,
    KnowledgeUnit,
    KnowledgeVersion,
    PermissionScope,
)


class PermissionGrantSchema(BaseModel):
    """四维权限规则 Schema。"""

    scope: PermissionScope = Field(..., description="权限类型")
    subject_id: str = Field(default="", description="部门、角色或用户 ID")
    include_descendants: bool = Field(default=False, description="部门权限是否包含下级")

    @classmethod
    def from_domain(cls, grant) -> "PermissionGrantSchema":
        """转换领域权限规则。"""
        return cls(
            scope=grant.scope,
            subject_id=grant.subject_id,
            include_descendants=grant.include_descendants,
        )


class CreateKnowledgeRequest(BaseModel):
    """创建知识草稿请求。"""

    title: str = Field(..., min_length=1)
    category_id: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)


class UpdateMetadataRequest(BaseModel):
    """更新知识元数据请求。"""

    title: str = Field(default="")
    category_id: str = Field(default="")
    tags: list[str] = Field(default_factory=list)


class CreateVersionRequest(BaseModel):
    """创建知识版本请求。"""

    source_object_key: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    content_type: str = Field(default="application/octet-stream")


class ConfigurePermissionsRequest(BaseModel):
    """配置四维权限请求。"""

    grants: list[PermissionGrantSchema] = Field(default_factory=list)


class KnowledgeActionResponse(BaseModel):
    """知识维护结果响应。"""

    knowledge_id: str
    status: str
    version_id: str = ""
    job_id: str = ""
    permission_version: int = 0

    @classmethod
    def from_result(cls, result: KnowledgeMaintenanceResult) -> "KnowledgeActionResponse":
        """构造响应。"""
        return cls(
            knowledge_id=result.knowledge_id,
            status=result.status.value,
            version_id=result.version_id,
            job_id=result.job_id,
            permission_version=result.permission_version,
        )


class KnowledgeUnitResponse(BaseModel):
    """知识单元列表/详情响应。"""

    knowledge_id: str
    title: str
    category_id: str
    tags: list[str]
    status: str
    current_version_id: str = ""
    created_by: str
    updated_by: str
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_domain(cls, unit: KnowledgeUnit) -> "KnowledgeUnitResponse":
        """转换知识单元。"""
        return cls(
            knowledge_id=unit.knowledge_id,
            title=unit.title,
            category_id=unit.category_id,
            tags=list(unit.tags),
            status=unit.status.value,
            current_version_id=unit.current_version_id,
            created_by=unit.created_by,
            updated_by=unit.updated_by,
            created_at=unit.created_at.isoformat() if unit.created_at else "",
            updated_at=unit.updated_at.isoformat() if unit.updated_at else "",
        )


class KnowledgeVersionResponse(BaseModel):
    """知识版本响应。"""

    version_id: str
    knowledge_id: str
    version_no: int
    source_object_key: str
    markdown_object_key: str = ""
    filename: str
    content_type: str
    status: str
    error_message: str = ""
    created_by: str
    created_at: str = ""

    @classmethod
    def from_domain(cls, version: KnowledgeVersion) -> "KnowledgeVersionResponse":
        """转换知识版本。"""
        return cls(
            version_id=version.version_id,
            knowledge_id=version.knowledge_id,
            version_no=version.version_no,
            source_object_key=version.source_object_key,
            markdown_object_key=version.markdown_object_key,
            filename=version.filename,
            content_type=version.content_type,
            status=version.status.value,
            error_message=version.error_message,
            created_by=version.created_by,
            created_at=version.created_at.isoformat() if version.created_at else "",
        )


class KnowledgePageResponse(BaseModel):
    """知识单元分页响应。"""

    items: list[KnowledgeUnitResponse]
    page: int
    page_size: int
    total: int


class PermissionSetResponse(BaseModel):
    """知识权限集合响应。"""

    knowledge_id: str
    permission_version: int
    grants: list[PermissionGrantSchema]

    @classmethod
    def from_domain(cls, permission_set: KnowledgePermissionSet) -> "PermissionSetResponse":
        """转换权限集合。"""
        return cls(
            knowledge_id=permission_set.knowledge_id,
            permission_version=permission_set.permission_version,
            grants=[PermissionGrantSchema.from_domain(item) for item in permission_set.grants],
        )

class KnowledgeChunkResponse(BaseModel):
    """知识切片预览响应。"""

    chunk_id: str
    version_id: str
    content: str
    section_path: str = ""
    image_summary: str = ""


class KnowledgePreviewResponse(BaseModel):
    """知识规范 Markdown 与切片预览响应。"""

    knowledge_id: str
    title: str
    version_id: str
    version_no: int
    markdown: str
    chunks: list[KnowledgeChunkResponse] = Field(default_factory=list)
