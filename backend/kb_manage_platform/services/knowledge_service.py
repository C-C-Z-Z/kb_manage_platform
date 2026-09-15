"""提供知识维护和四维权限配置应用服务。"""

from pathlib import PurePosixPath
from uuid import uuid4

from kb_manage_platform.domain.models import (
    KnowledgeAction,
    KnowledgeMaintenanceCommand,
    KnowledgeMaintenanceResult,
    KnowledgePermissionSet,
    KnowledgeStatus,
    KnowledgeUnit,
    KnowledgeVersion,
    PermissionGrant,
    PermissionScope,
    UserContext,
)
from kb_manage_platform.domain.ports import (
    KnowledgeGapRepositoryPort,
    KnowledgePermissionRepositoryPort,
    KnowledgeRepositoryPort,
    ObjectStoragePort,
    VectorIndexPort,
)
from kb_manage_platform.domain.services.permissions import PermissionPolicy
from kb_manage_platform.engines.knowledge_engine.main_graph import KnowledgeMaintenanceWorkflow


class KnowledgeService:
    """编排知识维护用例，不处理 HTTP DTO。"""

    def __init__(
        self,
        workflow: KnowledgeMaintenanceWorkflow,
        gap_repository: KnowledgeGapRepositoryPort,
        repository: KnowledgeRepositoryPort,
        permission_repository: KnowledgePermissionRepositoryPort,
        object_storage: ObjectStoragePort,
        raw_bucket: str,
        permission_policy: PermissionPolicy,
        markdown_bucket: str = "",
        image_bucket: str = "",
        vector_index: VectorIndexPort | None = None,
    ) -> None:
        self._workflow = workflow
        self._gap_repository = gap_repository
        self._repository = repository
        self._permission_repository = permission_repository
        self._object_storage = object_storage
        self._raw_bucket = raw_bucket
        self._markdown_bucket = markdown_bucket
        self._image_bucket = image_bucket
        self._permission_policy = permission_policy
        self._vector_index = vector_index

    async def list_units(
        self,
        user: UserContext,
        query: str,
        status: KnowledgeStatus | None,
        category_id: str,
        page: int,
        page_size: int,
    ) -> tuple[tuple[KnowledgeUnit, ...], int]:
        """按四维权限过滤后返回知识单元页。"""
        units, _ = await self._repository.list_units(query, status, category_id, 1, 1000)
        permission_sets = await self._permission_repository.list_grants_batch(
            tuple(unit.knowledge_id for unit in units)
        )
        allowed = [
            unit
            for unit in units
            if self._permission_policy.matches(
                user,
                permission_sets.get(unit.knowledge_id, KnowledgePermissionSet(unit.knowledge_id, ())).grants,
            )
        ]
        start = (page - 1) * page_size
        return tuple(allowed[start : start + page_size]), len(allowed)

    async def get_unit(self, knowledge_id: str, user: UserContext) -> KnowledgeUnit:
        """返回当前用户有权访问的知识单元。"""
        unit = await self._repository.get_unit(knowledge_id)
        if unit is None:
            raise LookupError(f"knowledge not found: {knowledge_id}")
        await self._ensure_allowed(knowledge_id, user)
        return unit

    async def list_versions(
        self, knowledge_id: str, user: UserContext
    ) -> tuple[KnowledgeVersion, ...]:
        """返回当前用户有权访问的版本列表。"""
        await self.get_unit(knowledge_id, user)
        return await self._repository.list_versions(knowledge_id)

    async def list_permissions(
        self, knowledge_id: str, user: UserContext
    ) -> KnowledgePermissionSet:
        """返回当前用户有权查看的权限集合。"""
        await self.get_unit(knowledge_id, user)
        return await self._permission_repository.list_grants(knowledge_id)

    async def preview(
        self,
        knowledge_id: str,
        version_id: str,
        user: UserContext,
    ) -> tuple[KnowledgeUnit, KnowledgeVersion, bytes, tuple]:
        """返回有权访问版本的规范 Markdown 与切片。"""
        unit = await self.get_unit(knowledge_id, user)
        version = (
            await self._repository.get_version(knowledge_id, version_id)
            if version_id
            else await self._repository.get_current_version(knowledge_id)
        )
        if version is None:
            raise LookupError(f"knowledge version not found: {version_id or knowledge_id}")
        if not version.markdown_object_key:
            raise ValueError("version markdown is not available")
        markdown = await self._object_storage.get_bytes(
            self._markdown_bucket or self._raw_bucket,
            version.markdown_object_key,
        )
        chunks: tuple = ()
        if self._vector_index is not None and version.status.value == "indexed":
            chunks = tuple(await self._vector_index.list_chunks(knowledge_id))
        return unit, version, markdown, chunks

    async def download(
        self,
        knowledge_id: str,
        version_id: str,
        user: UserContext,
    ) -> tuple[KnowledgeVersion, bytes]:
        """返回有权访问版本的原文件。"""
        await self.get_unit(knowledge_id, user)
        version = (
            await self._repository.get_version(knowledge_id, version_id)
            if version_id
            else await self._repository.get_current_version(knowledge_id)
        )
        if version is None:
            raise LookupError(f"knowledge version not found: {version_id or knowledge_id}")
        content = await self._object_storage.get_bytes(
            self._raw_bucket,
            version.source_object_key,
        )
        return version, content

    async def rollback_version(
        self,
        knowledge_id: str,
        version_id: str,
        user: UserContext,
    ) -> KnowledgeVersion:
        """将已索引历史版本切换为当前检索版本。"""
        await self._ensure_allowed(knowledge_id, user)
        return await self._repository.activate_version(knowledge_id, version_id, user.user_id)

    async def delete(self, knowledge_id: str, user: UserContext) -> None:
        """删除知识数据库、对象存储和向量数据。"""
        await self._ensure_allowed(knowledge_id, user)
        if self._vector_index is not None:
            await self._vector_index.delete_knowledge(knowledge_id)
        prefix = f"knowledge/{knowledge_id}/"
        await self._object_storage.delete_prefix(self._raw_bucket, prefix)
        await self._object_storage.delete_prefix(self._markdown_bucket or self._raw_bucket, prefix)
        if self._image_bucket:
            await self._object_storage.delete_prefix(self._image_bucket, prefix)
        await self._repository.delete_unit(knowledge_id)

    async def _ensure_allowed(self, knowledge_id: str, user: UserContext) -> None:
        """校验当前用户是否具备知识数据权限。"""
        permission_set = await self._permission_repository.list_grants(knowledge_id)
        if not self._permission_policy.matches(user, permission_set.grants):
            raise PermissionError("knowledge access denied")

    async def archive(self, knowledge_id: str, user: UserContext) -> KnowledgeMaintenanceResult:
        """将有权访问的知识单元置为归档状态。"""
        await self._ensure_allowed(knowledge_id, user)
        return await self._run(KnowledgeAction.ARCHIVE, user.user_id, knowledge_id=knowledge_id)

    async def upload_version(
        self,
        knowledge_id: str,
        filename: str,
        content_type: str,
        content: bytes,
        user: UserContext,
    ) -> KnowledgeMaintenanceResult:
        """保存文件到 MinIO 后执行创建版本用例。"""
        await self._ensure_allowed(knowledge_id, user)
        safe_name = PurePosixPath(filename).name
        if not safe_name:
            raise ValueError("filename must not be empty")
        version_id = str(uuid4())
        object_key = f"knowledge/{knowledge_id}/{version_id}/{safe_name}"
        await self._object_storage.put_bytes(
            self._raw_bucket,
            object_key,
            content,
            content_type or "application/octet-stream",
        )
        return await self.create_version(
            knowledge_id,
            object_key,
            safe_name,
            content_type or "application/octet-stream",
            user,
        )

    async def create(
        self, title: str, category_id: str, tags: tuple[str, ...], user: UserContext
    ) -> KnowledgeMaintenanceResult:
        """创建知识草稿并授予创建者个人访问权限。"""
        result = await self._run(
            KnowledgeAction.CREATE,
            user.user_id,
            title=title,
            category_id=category_id,
            tags=tags,
        )
        await self._permission_repository.replace_grants(
            result.knowledge_id,
            (PermissionGrant(PermissionScope.USER, user.user_id, False),),
            user.user_id,
        )
        return result

    async def update_metadata(
        self,
        knowledge_id: str,
        title: str,
        category_id: str,
        tags: tuple[str, ...],
        user: UserContext,
    ) -> KnowledgeMaintenanceResult:
        """更新有权访问的知识元数据。"""
        await self._ensure_allowed(knowledge_id, user)
        return await self._run(
            KnowledgeAction.UPDATE_METADATA,
            user.user_id,
            knowledge_id=knowledge_id,
            title=title,
            category_id=category_id,
            tags=tags,
        )

    async def create_version(
        self,
        knowledge_id: str,
        source_object_key: str,
        filename: str,
        content_type: str,
        user: UserContext,
    ) -> KnowledgeMaintenanceResult:
        """创建有权访问知识的新版本。"""
        await self._ensure_allowed(knowledge_id, user)
        return await self._run(
            KnowledgeAction.CREATE_VERSION,
            user.user_id,
            knowledge_id=knowledge_id,
            source_object_key=source_object_key,
            filename=filename,
            content_type=content_type,
        )

    async def configure_permissions(
        self,
        knowledge_id: str,
        grants: tuple[PermissionGrant, ...],
        user: UserContext,
    ) -> KnowledgeMaintenanceResult:
        """配置有权访问知识的四维权限。"""
        await self._ensure_allowed(knowledge_id, user)
        return await self._run(
            KnowledgeAction.CONFIGURE_PERMISSIONS,
            user.user_id,
            knowledge_id=knowledge_id,
            grants=grants,
        )

    async def publish(self, knowledge_id: str, user: UserContext) -> KnowledgeMaintenanceResult:
        """发布有权访问的知识并关闭关联缺口。"""
        await self._ensure_allowed(knowledge_id, user)
        result = await self._run(KnowledgeAction.PUBLISH, user.user_id, knowledge_id=knowledge_id)
        await self._gap_repository.resolve_by_knowledge(knowledge_id)
        return result

    async def disable(self, knowledge_id: str, user: UserContext) -> KnowledgeMaintenanceResult:
        """停用有权访问的知识。"""
        await self._ensure_allowed(knowledge_id, user)
        return await self._run(KnowledgeAction.DISABLE, user.user_id, knowledge_id=knowledge_id)

    async def _run(
        self, action: KnowledgeAction, operator_id: str, **payload
    ) -> KnowledgeMaintenanceResult:
        """执行知识维护工作流。"""
        command = KnowledgeMaintenanceCommand(
            action=action,
            request_id=str(uuid4()),
            operator_id=operator_id,
            **payload,
        )
        state = await self._workflow.ainvoke({"command": command})
        return state["result"]

