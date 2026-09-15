"""模型服务和系统参数配置路由。"""

from fastapi import APIRouter

from kb_manage_platform.api.dependencies import (
    ConfigurationServiceDep,
    ModelManageUserDep,
    SystemManageUserDep,
)
from kb_manage_platform.api.schemas.configuration import (
    ModelConfigResponse,
    ModelTestResponse,
    SaveModelConfigRequest,
    SaveSystemSettingRequest,
    SystemSettingResponse,
)

router = APIRouter(prefix="/system", tags=["system-configuration"])


@router.get("/model-configs", response_model=list[ModelConfigResponse])
async def list_model_configs(
    _: ModelManageUserDep,
    service: ConfigurationServiceDep,
) -> list[ModelConfigResponse]:
    return [ModelConfigResponse(**item) for item in await service.list_models()]


@router.put("/model-configs/{model_type}", response_model=ModelConfigResponse)
async def save_model_config(
    model_type: str,
    payload: SaveModelConfigRequest,
    user: ModelManageUserDep,
    service: ConfigurationServiceDep,
) -> ModelConfigResponse:
    item = await service.save_model(
        model_type,
        payload.name,
        payload.base_url,
        payload.model_name,
        payload.api_key,
        payload.options,
        payload.status,
        user.user_id,
    )
    return ModelConfigResponse(**item)


@router.post("/model-configs/{model_type}/test", response_model=ModelTestResponse)
async def test_model_config(
    model_type: str,
    user: ModelManageUserDep,
    service: ConfigurationServiceDep,
) -> ModelTestResponse:
    return ModelTestResponse(**await service.test_model(model_type, user.user_id))


@router.get("/settings", response_model=list[SystemSettingResponse])
async def list_system_settings(
    _: SystemManageUserDep,
    service: ConfigurationServiceDep,
) -> list[SystemSettingResponse]:
    return [SystemSettingResponse(**item) for item in await service.list_settings()]


@router.put("/settings/{setting_key}", response_model=SystemSettingResponse)
async def save_system_setting(
    setting_key: str,
    payload: SaveSystemSettingRequest,
    user: SystemManageUserDep,
    service: ConfigurationServiceDep,
) -> SystemSettingResponse:
    item = await service.save_setting(
        setting_key, payload.value, payload.description, user.user_id
    )
    return SystemSettingResponse(
        setting_key=item.setting_key,
        value=item.value,
        description=item.description,
        updated_by=item.updated_by,
        updated_at=item.updated_at.isoformat() if item.updated_at else "",
    )
