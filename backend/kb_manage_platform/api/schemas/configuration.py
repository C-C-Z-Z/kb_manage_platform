"""模型和系统配置 API 模型。"""

from typing import Any

from pydantic import BaseModel, Field


class ModelConfigResponse(BaseModel):
    config_id: str = ""
    model_type: str
    name: str
    base_url: str
    model_name: str
    status: str
    source: str
    effective_source: str
    runtime_applied: bool = False
    api_key_masked: str = ""
    local_model_path: str = ""
    options: dict[str, Any] = Field(default_factory=dict)


class SaveModelConfigRequest(BaseModel):
    name: str = Field(..., min_length=1)
    base_url: str = ""
    model_name: str = Field(..., min_length=1)
    api_key: str = ""
    options: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="active", pattern="^(active|disabled)$")


class ModelTestResponse(BaseModel):
    model_type: str
    success: bool
    message: str


class SystemSettingResponse(BaseModel):
    setting_key: str
    value: Any
    description: str = ""
    updated_by: str = ""
    updated_at: str = ""


class SaveSystemSettingRequest(BaseModel):
    value: Any
    description: str = ""
