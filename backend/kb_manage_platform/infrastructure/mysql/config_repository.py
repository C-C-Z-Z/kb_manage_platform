"""实现模型配置和系统参数的 MySQL 仓储。"""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.domain.models import ModelConfig, SystemSetting
from kb_manage_platform.infrastructure.mysql.models import ModelConfigModel, SystemSettingModel


class MysqlModelConfigRepository:
    """模型配置仓储。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_all(self) -> tuple[ModelConfig, ...]:
        async with self._session_factory() as session:
            rows = (await session.scalars(select(ModelConfigModel).order_by(ModelConfigModel.model_type))).all()
        return tuple(self._to_domain(row) for row in rows)

    async def get(self, model_type: str) -> ModelConfig | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(ModelConfigModel).where(ModelConfigModel.model_type == model_type)
            )
        return self._to_domain(row) if row else None

    async def upsert(
        self,
        model_type: str,
        name: str,
        base_url: str,
        model_name: str,
        api_key_ciphertext: str,
        options: dict[str, object],
        status: str,
        operator_id: str,
    ) -> ModelConfig:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(ModelConfigModel).where(ModelConfigModel.model_type == model_type)
            )
            if row is None:
                row = ModelConfigModel(
                    config_id=str(uuid4()),
                    model_type=model_type,
                    name=name.strip(),
                    base_url=base_url.strip().rstrip("/"),
                    model_name=model_name.strip(),
                    api_key_ciphertext=api_key_ciphertext,
                    options=dict(options),
                    status=status,
                    updated_by=operator_id,
                )
                session.add(row)
            else:
                row.name = name.strip()
                row.base_url = base_url.strip().rstrip("/")
                row.model_name = model_name.strip()
                row.api_key_ciphertext = api_key_ciphertext
                row.options = dict(options)
                row.status = status
                row.updated_by = operator_id
            await session.commit()
            await session.refresh(row)
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: ModelConfigModel) -> ModelConfig:
        return ModelConfig(
            config_id=row.config_id,
            model_type=row.model_type,
            name=row.name,
            base_url=row.base_url,
            model_name=row.model_name,
            api_key_ciphertext=row.api_key_ciphertext,
            options=dict(row.options or {}),
            status=row.status,
            updated_by=row.updated_by,
            updated_at=row.updated_at,
        )


class MysqlSystemSettingRepository:
    """系统参数仓储。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_all(self) -> tuple[SystemSetting, ...]:
        async with self._session_factory() as session:
            rows = (await session.scalars(select(SystemSettingModel).order_by(SystemSettingModel.setting_key))).all()
        return tuple(self._to_domain(row) for row in rows)

    async def upsert(
        self, setting_key: str, value: object, description: str, operator_id: str
    ) -> SystemSetting:
        async with self._session_factory() as session:
            row = await session.get(SystemSettingModel, setting_key)
            if row is None:
                row = SystemSettingModel(
                    setting_key=setting_key,
                    value=value,
                    description=description,
                    updated_by=operator_id,
                )
                session.add(row)
            else:
                row.value = value
                row.description = description
                row.updated_by = operator_id
            await session.commit()
            await session.refresh(row)
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: SystemSettingModel) -> SystemSetting:
        return SystemSetting(
            setting_key=row.setting_key,
            value=row.value,
            description=row.description,
            updated_by=row.updated_by,
            updated_at=row.updated_at,
        )
