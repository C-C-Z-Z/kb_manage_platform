"""知识维护与四维权限配置路由。"""

from urllib.parse import quote

from fastapi import APIRouter, File, Response, UploadFile

from kb_manage_platform.api.dependencies import (
    KnowledgeCreateUserDep,
    KnowledgeDisableUserDep,
    KnowledgeDownloadUserDep,
    KnowledgePermissionUserDep,
    KnowledgePublishUserDep,
    KnowledgeReadUserDep,
    KnowledgeServiceDep,
    KnowledgeUpdateUserDep,
)
from kb_manage_platform.api.schemas.knowledge import (
    ConfigurePermissionsRequest,
    CreateKnowledgeRequest,
    CreateVersionRequest,
    KnowledgeActionResponse,
    KnowledgeChunkResponse,
    KnowledgePageResponse,
    KnowledgePreviewResponse,
    KnowledgeUnitResponse,
    KnowledgeVersionResponse,
    PermissionSetResponse,
    UpdateMetadataRequest,
)
from kb_manage_platform.common.errors import ValidationError
from kb_manage_platform.domain.models import KnowledgeStatus, PermissionGrant

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=KnowledgePageResponse)
async def list_knowledge(
    _: KnowledgeReadUserDep,
    service: KnowledgeServiceDep,
    query: str = "",
    status: str = "",
    category_id: str = "",
    page: int = 1,
    page_size: int = 20,
) -> KnowledgePageResponse:
    """分页查询知识台账。"""
    normalized_page = max(1, page)
    normalized_size = max(1, min(page_size, 100))
    parsed_status: KnowledgeStatus | None
    try:
        parsed_status = KnowledgeStatus(status) if status else None
    except ValueError as exc:
        raise ValidationError("invalid knowledge status") from exc
    units, total = await service.list_units(
        _, query, parsed_status, category_id, normalized_page, normalized_size
    )
    return KnowledgePageResponse(
        items=[KnowledgeUnitResponse.from_domain(item) for item in units],
        page=normalized_page,
        page_size=normalized_size,
        total=total,
    )


@router.post("", response_model=KnowledgeActionResponse)
async def create_knowledge(
    payload: CreateKnowledgeRequest,
    user: KnowledgeCreateUserDep,
    service: KnowledgeServiceDep,
) -> KnowledgeActionResponse:
    """创建知识草稿。"""
    result = await service.create(payload.title, payload.category_id, tuple(payload.tags), user)
    return KnowledgeActionResponse.from_result(result)


@router.get("/{knowledge_id}", response_model=KnowledgeUnitResponse)
async def get_knowledge(
    knowledge_id: str,
    _: KnowledgeReadUserDep,
    service: KnowledgeServiceDep,
) -> KnowledgeUnitResponse:
    """查询知识详情。"""
    return KnowledgeUnitResponse.from_domain(await service.get_unit(knowledge_id, _))


@router.patch("/{knowledge_id}", response_model=KnowledgeActionResponse)
async def update_knowledge(
    knowledge_id: str,
    payload: UpdateMetadataRequest,
    user: KnowledgeUpdateUserDep,
    service: KnowledgeServiceDep,
) -> KnowledgeActionResponse:
    """更新知识元数据。"""
    result = await service.update_metadata(
        knowledge_id, payload.title, payload.category_id, tuple(payload.tags), user
    )
    return KnowledgeActionResponse.from_result(result)


@router.get("/{knowledge_id}/versions", response_model=list[KnowledgeVersionResponse])
async def list_versions(
    knowledge_id: str,
    _: KnowledgeReadUserDep,
    service: KnowledgeServiceDep,
) -> list[KnowledgeVersionResponse]:
    """查询知识版本历史。"""
    versions = await service.list_versions(knowledge_id, _)
    return [KnowledgeVersionResponse.from_domain(item) for item in versions]


@router.post("/{knowledge_id}/versions", response_model=KnowledgeActionResponse)
async def create_version(
    knowledge_id: str,
    payload: CreateVersionRequest,
    user: KnowledgeUpdateUserDep,
    service: KnowledgeServiceDep,
) -> KnowledgeActionResponse:
    """为已存在对象创建知识版本。"""
    result = await service.create_version(
        knowledge_id,
        payload.source_object_key,
        payload.filename,
        payload.content_type,
        user,
    )
    return KnowledgeActionResponse.from_result(result)


@router.post("/{knowledge_id}/versions/upload", response_model=KnowledgeActionResponse)
async def upload_version(
    knowledge_id: str,
    user: KnowledgeUpdateUserDep,
    service: KnowledgeServiceDep,
    file: UploadFile = File(...),
) -> KnowledgeActionResponse:
    """上传文件并创建异步入库任务。"""
    content = await file.read()
    if not content:
        raise ValidationError("file must not be empty")
    result = await service.upload_version(
        knowledge_id,
        file.filename or "document",
        file.content_type or "application/octet-stream",
        content,
        user,
    )
    return KnowledgeActionResponse.from_result(result)


@router.get("/{knowledge_id}/preview", response_model=KnowledgePreviewResponse)
async def preview_knowledge(
    knowledge_id: str,
    _: KnowledgeReadUserDep,
    service: KnowledgeServiceDep,
    version_id: str = "",
) -> KnowledgePreviewResponse:
    """返回有权访问版本的规范 Markdown 和切片。"""
    unit, version, content, chunks = await service.preview(knowledge_id, version_id, _)
    return KnowledgePreviewResponse(
        knowledge_id=unit.knowledge_id,
        title=unit.title,
        version_id=version.version_id,
        version_no=version.version_no,
        markdown=content.decode("utf-8", errors="replace"),
        chunks=[
            KnowledgeChunkResponse(
                chunk_id=item.chunk_id,
                version_id=item.version_id,
                content=item.content,
                section_path=item.section_path,
                image_summary=item.image_summary,
            )
            for item in chunks
        ],
    )


@router.get("/{knowledge_id}/download")
async def download_knowledge(
    knowledge_id: str,
    _: KnowledgeDownloadUserDep,
    service: KnowledgeServiceDep,
    version_id: str = "",
) -> Response:
    """下载有权访问版本的原文件。"""
    version, content = await service.download(knowledge_id, version_id, _)
    encoded_name = quote(version.filename)
    return Response(
        content=content,
        media_type=version.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


@router.post(
    "/{knowledge_id}/versions/{version_id}/rollback",
    response_model=KnowledgeVersionResponse,
)
async def rollback_version(
    knowledge_id: str,
    version_id: str,
    user: KnowledgeUpdateUserDep,
    service: KnowledgeServiceDep,
) -> KnowledgeVersionResponse:
    """回滚到已索引历史版本。"""
    version = await service.rollback_version(knowledge_id, version_id, user)
    return KnowledgeVersionResponse.from_domain(version)


@router.delete("/{knowledge_id}", status_code=204)
async def delete_knowledge(
    knowledge_id: str,
    user: KnowledgeDisableUserDep,
    service: KnowledgeServiceDep,
) -> None:
    """物理删除知识及其派生资源。"""
    await service.delete(knowledge_id, user)


@router.get("/{knowledge_id}/permissions", response_model=PermissionSetResponse)
async def get_permissions(
    knowledge_id: str,
    _: KnowledgeReadUserDep,
    service: KnowledgeServiceDep,
) -> PermissionSetResponse:
    """查询知识四维权限。"""
    return PermissionSetResponse.from_domain(await service.list_permissions(knowledge_id, _))


@router.put("/{knowledge_id}/permissions", response_model=KnowledgeActionResponse)
async def configure_permissions(
    knowledge_id: str,
    payload: ConfigurePermissionsRequest,
    user: KnowledgePermissionUserDep,
    service: KnowledgeServiceDep,
) -> KnowledgeActionResponse:
    """配置四维数据权限。"""
    grants = tuple(
        PermissionGrant(item.scope, item.subject_id, item.include_descendants)
        for item in payload.grants
    )
    result = await service.configure_permissions(knowledge_id, grants, user)
    return KnowledgeActionResponse.from_result(result)


@router.post("/{knowledge_id}/publish", response_model=KnowledgeActionResponse)
async def publish_knowledge(
    knowledge_id: str,
    user: KnowledgePublishUserDep,
    service: KnowledgeServiceDep,
) -> KnowledgeActionResponse:
    """发布知识。"""
    return KnowledgeActionResponse.from_result(await service.publish(knowledge_id, user))


@router.post("/{knowledge_id}/disable", response_model=KnowledgeActionResponse)
async def disable_knowledge(
    knowledge_id: str,
    user: KnowledgeDisableUserDep,
    service: KnowledgeServiceDep,
) -> KnowledgeActionResponse:
    """停用知识。"""
    return KnowledgeActionResponse.from_result(await service.disable(knowledge_id, user))


@router.post("/{knowledge_id}/archive", response_model=KnowledgeActionResponse)
async def archive_knowledge(
    knowledge_id: str,
    user: KnowledgeDisableUserDep,
    service: KnowledgeServiceDep,
) -> KnowledgeActionResponse:
    """归档知识。"""
    return KnowledgeActionResponse.from_result(await service.archive(knowledge_id, user))




