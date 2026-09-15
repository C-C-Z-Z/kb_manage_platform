"""实现知识单元与版本文档的 MySQL 仓储。"""

from uuid import uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.infrastructure.mysql.models import (
    KnowledgePermissionModel,
    KnowledgeUnitModel,
    KnowledgeVersionModel,
)
from kb_manage_platform.domain.models import (
    KnowledgeMaintenanceCommand,
    KnowledgeStatus,
    KnowledgeUnit,
    KnowledgeVersion,
    VersionStatus,
)


class MysqlKnowledgeRepository:
    """基于 SQLAlchemy AsyncSession 的知识仓储。"""

    # 作用：保存异步会话工厂。
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：创建知识单元草稿。
    async def create_unit(self, command: KnowledgeMaintenanceCommand) -> KnowledgeUnit:
        """写入 knowledge_unit 表。"""
        model = KnowledgeUnitModel(
            knowledge_id=command.knowledge_id or str(uuid4()),
            title=command.title.strip(),
            category_id=command.category_id,
            tags=list(command.tags),
            status=KnowledgeStatus.DRAFT.value,
            created_by=command.operator_id,
            updated_by=command.operator_id,
        )
        async with self._session_factory() as session:
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._to_unit(model)

    # 作用：按知识 ID 获取知识单元。
    async def get_unit(self, knowledge_id: str) -> KnowledgeUnit | None:
        """查询 knowledge_unit 表。"""
        async with self._session_factory() as session:
            model = await session.get(KnowledgeUnitModel, knowledge_id)
            return self._to_unit(model) if model else None

    # 作用：更新知识单元元数据。
    async def update_metadata(
        self,
        knowledge_id: str,
        title: str,
        category_id: str,
        tags: tuple[str, ...],
        operator_id: str,
    ) -> KnowledgeUnit:
        """更新标题、分类和标签。"""
        async with self._session_factory() as session:
            model = await session.get(KnowledgeUnitModel, knowledge_id)
            if model is None:
                raise LookupError(f"knowledge not found: {knowledge_id}")
            model.title = title.strip()
            model.category_id = category_id
            model.tags = list(tags)
            model.updated_by = operator_id
            await session.commit()
            await session.refresh(model)
            return self._to_unit(model)

    # 作用：创建新的知识版本文档。
    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        """写入 knowledge_version 表并更新当前版本指针。"""
        async with self._session_factory() as session:
            max_version = await session.scalar(
                select(func.max(KnowledgeVersionModel.version_no)).where(
                    KnowledgeVersionModel.knowledge_id == version.knowledge_id
                )
            )
            model = KnowledgeVersionModel(
                version_id=version.version_id,
                knowledge_id=version.knowledge_id,
                version_no=(max_version or 0) + 1,
                source_object_key=version.source_object_key,
                markdown_object_key=version.markdown_object_key,
                filename=version.filename,
                content_type=version.content_type,
                status=version.status.value,
                error_message=version.error_message,
                created_by=version.created_by,
            )
            session.add(model)
            unit = await session.get(KnowledgeUnitModel, version.knowledge_id)
            if unit is None:
                raise LookupError(f"knowledge not found: {version.knowledge_id}")
            unit.current_version_id = version.version_id
            unit.updated_by = version.created_by
            await session.commit()
            await session.refresh(model)
            return self._to_version(model)

    # 作用：获取知识单元当前版本。
    async def get_current_version(self, knowledge_id: str) -> KnowledgeVersion | None:
        """查询 knowledge_version 表。"""
        async with self._session_factory() as session:
            unit = await session.get(KnowledgeUnitModel, knowledge_id)
            if unit is None or not unit.current_version_id:
                return None
            model = await session.get(KnowledgeVersionModel, unit.current_version_id)
            return self._to_version(model) if model else None

    # 作用：分页查询知识单元并支持标题、分类和状态过滤。
    async def list_units(
        self,
        query: str,
        status: KnowledgeStatus | None,
        category_id: str,
        page: int,
        page_size: int,
    ) -> tuple[tuple[KnowledgeUnit, ...], int]:
        """返回知识单元页和总数。"""
        conditions = []
        if query.strip():
            pattern = f"%{query.strip()}%"
            conditions.append(or_(KnowledgeUnitModel.title.like(pattern), KnowledgeUnitModel.knowledge_id.like(pattern)))
        if status is not None:
            conditions.append(KnowledgeUnitModel.status == status.value)
        if category_id.strip():
            conditions.append(KnowledgeUnitModel.category_id == category_id.strip())

        async with self._session_factory() as session:
            count_stmt = select(func.count()).select_from(KnowledgeUnitModel)
            list_stmt = select(KnowledgeUnitModel)
            if conditions:
                count_stmt = count_stmt.where(*conditions)
                list_stmt = list_stmt.where(*conditions)
            total = int(await session.scalar(count_stmt) or 0)
            rows = (
                await session.scalars(
                    list_stmt
                    .order_by(KnowledgeUnitModel.updated_at.desc(), KnowledgeUnitModel.knowledge_id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        return tuple(self._to_unit(row) for row in rows), total

    # 作用：按知识 ID 查询全部历史版本。
    async def list_versions(self, knowledge_id: str) -> tuple[KnowledgeVersion, ...]:
        """返回按版本号倒序排列的版本文档。"""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(KnowledgeVersionModel)
                    .where(KnowledgeVersionModel.knowledge_id == knowledge_id)
                    .order_by(KnowledgeVersionModel.version_no.desc())
                )
            ).all()
        return tuple(self._to_version(row) for row in rows)

    # 作用：更新知识单元生命周期状态。
    async def set_unit_status(
        self, knowledge_id: str, status: KnowledgeStatus, operator_id: str
    ) -> KnowledgeUnit:
        """更新 knowledge_unit 状态。"""
        async with self._session_factory() as session:
            model = await session.get(KnowledgeUnitModel, knowledge_id)
            if model is None:
                raise LookupError(f"knowledge not found: {knowledge_id}")
            model.status = status.value
            model.updated_by = operator_id
            await session.commit()
            await session.refresh(model)
            return self._to_unit(model)

    # 作用：更新版本文档状态，供导入 Worker 发布索引结果。
    async def save_version(
        self, request_id: str, knowledge_id: str, version_id: str, state: str
    ) -> None:
        """更新 knowledge_version 状态。"""
        async with self._session_factory() as session:
            model = await session.get(KnowledgeVersionModel, version_id)
            if model is None or model.knowledge_id != knowledge_id:
                raise LookupError(f"knowledge version not found: {version_id}")
            model.status = state
            await session.commit()
    # 作用：按版本 ID 获取知识版本文档。
    async def get_version(self, knowledge_id: str, version_id: str) -> KnowledgeVersion | None:
        """查询指定知识的单个版本。"""
        async with self._session_factory() as session:
            model = await session.get(KnowledgeVersionModel, version_id)
            if model is None or model.knowledge_id != knowledge_id:
                return None
            return self._to_version(model)

    # 作用：将已索引历史版本切换为当前版本。
    async def activate_version(
        self, knowledge_id: str, version_id: str, operator_id: str
    ) -> KnowledgeVersion:
        """原子切换 knowledge_unit.current_version_id。"""
        async with self._session_factory() as session:
            version = await session.get(KnowledgeVersionModel, version_id)
            if version is None or version.knowledge_id != knowledge_id:
                raise LookupError(f"knowledge version not found: {version_id}")
            if version.status != VersionStatus.INDEXED.value:
                raise ValueError("only indexed versions can be rolled back")
            unit = await session.get(KnowledgeUnitModel, knowledge_id)
            if unit is None:
                raise LookupError(f"knowledge not found: {knowledge_id}")
            unit.current_version_id = version_id
            unit.updated_by = operator_id
            await session.commit()
            await session.refresh(version)
            return self._to_version(version)

    # 作用：物理删除知识单元、版本和权限记录。
    async def delete_unit(self, knowledge_id: str) -> None:
        """删除知识管理相关数据库记录。"""
        async with self._session_factory() as session:
            unit = await session.get(KnowledgeUnitModel, knowledge_id)
            if unit is None:
                raise LookupError(f"knowledge not found: {knowledge_id}")
            await session.execute(
                delete(KnowledgePermissionModel).where(
                    KnowledgePermissionModel.knowledge_id == knowledge_id
                )
            )
            await session.execute(
                delete(KnowledgeVersionModel).where(
                    KnowledgeVersionModel.knowledge_id == knowledge_id
                )
            )
            await session.delete(unit)
            await session.commit()

    # 作用：将 ORM 知识单元转换为领域模型。
    @staticmethod
    def _to_unit(model: KnowledgeUnitModel) -> KnowledgeUnit:
        """转换知识单元模型。"""
        return KnowledgeUnit(
            knowledge_id=model.knowledge_id,
            title=model.title,
            category_id=model.category_id,
            tags=tuple(model.tags or []),
            status=KnowledgeStatus(model.status),
            current_version_id=model.current_version_id or "",
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # 作用：将 ORM 版本转换为领域模型。
    @staticmethod
    def _to_version(model: KnowledgeVersionModel) -> KnowledgeVersion:
        """转换版本文档模型。"""
        return KnowledgeVersion(
            version_id=model.version_id,
            knowledge_id=model.knowledge_id,
            version_no=model.version_no,
            source_object_key=model.source_object_key,
            markdown_object_key=model.markdown_object_key,
            filename=model.filename,
            content_type=model.content_type,
            status=VersionStatus(model.status),
            error_message=model.error_message,
            created_by=model.created_by,
            created_at=model.created_at,
        )


