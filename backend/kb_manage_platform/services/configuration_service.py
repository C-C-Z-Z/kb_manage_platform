"""提供模型服务和系统参数配置用例。"""

from pathlib import Path
from typing import Any

import httpx

from kb_manage_platform.bootstrap.settings import Settings
from kb_manage_platform.domain.models import ModelConfig, ResolvedModelConfig, SystemSetting
from kb_manage_platform.domain.ports import (
    AuditPort,
    ModelConfigRepositoryPort,
    ModelRuntimePort,
    SecretCipherPort,
    SystemSettingRepositoryPort,
)


class ConfigurationService:
    """管理模型连接参数和可热更新的系统参数。"""

    _MODEL_TYPES = {"llm", "embedding", "reranker", "vlm"}

    def __init__(
        self,
        settings: Settings,
        model_repository: ModelConfigRepositoryPort,
        setting_repository: SystemSettingRepositoryPort,
        cipher: SecretCipherPort,
        audit: AuditPort,
        runtime: ModelRuntimePort | None = None,
    ) -> None:
        self._settings = settings
        self._model_repository = model_repository
        self._setting_repository = setting_repository
        self._cipher = cipher
        self._audit = audit
        self._runtime = runtime
        self._runtime_applied: dict[str, bool] = {}

    async def list_models(self) -> list[dict[str, Any]]:
        """返回环境默认配置和数据库覆盖配置。"""
        defaults = self._default_models()
        stored = {item.model_type: item for item in await self._model_repository.list_all()}
        result: list[dict[str, Any]] = []
        for model_type, default in defaults.items():
            item = stored.get(model_type)
            result.append(self._to_model_view(model_type, default, item))
        return result

    # 作用：启动时加载数据库覆盖配置，未配置或停用时保持环境默认值。
    async def initialize_runtime(self) -> None:
        """将数据库模型配置应用到运行时适配器。"""
        stored = {item.model_type: item for item in await self._model_repository.list_all()}
        for model_type in self._MODEL_TYPES:
            await self._apply_model_to_runtime(model_type, stored.get(model_type))

    async def save_model(
        self,
        model_type: str,
        name: str,
        base_url: str,
        model_name: str,
        api_key: str,
        options: dict[str, Any],
        status: str,
        operator_id: str,
    ) -> dict[str, Any]:
        """保存模型配置。空 API Key 表示沿用现有密钥。"""
        if model_type not in self._MODEL_TYPES:
            raise ValueError(f"unsupported model type: {model_type}")
        existing = await self._model_repository.get(model_type)
        if not api_key and existing is not None:
            encrypted = existing.api_key_ciphertext
        elif not api_key:
            encrypted = self._cipher.encrypt(self._default_api_key(model_type))
        else:
            encrypted = self._cipher.encrypt(api_key)
        item = await self._model_repository.upsert(
            model_type,
            name,
            base_url,
            model_name,
            encrypted,
            options,
            status,
            operator_id,
        )
        await self._apply_model_to_runtime(model_type, item)
        await self._audit.record(
            "model.configured",
            {"user_id": operator_id, "model_type": model_type, "model_name": model_name},
        )
        return self._to_model_view(model_type, self._default_models()[model_type], item)

    async def test_model(self, model_type: str, operator_id: str) -> dict[str, Any]:
        """测试模型接口或本地模型路径。"""
        item = await self._resolved_model(model_type)
        ok = False
        message = ""
        try:
            if model_type == "embedding" and item["local_model_path"]:
                ok = Path(str(item["local_model_path"])).exists()
                message = "本地模型路径可用" if ok else "本地模型路径不存在"
            else:
                async with httpx.AsyncClient(timeout=httpx.Timeout(15)) as client:
                    if model_type == "reranker":
                        endpoint = self._model_endpoint(item["base_url"], "rerank")
                        payload = {
                            "model": item["model_name"],
                            "query": "连接测试",
                            "documents": ["测试文档"],
                            "top_n": 1,
                        }
                        if "/services/rerank/" in endpoint:
                            payload = {
                                "model": item["model_name"],
                                "input": {"query": "连接测试", "documents": ["测试文档"]},
                                "parameters": {"return_documents": False, "top_n": 1},
                            }
                        response = await client.post(
                            endpoint,
                            headers={"Authorization": f"Bearer {item['api_key']}"},
                            json=payload,
                        )
                    else:
                        response = await client.get(
                            self._model_endpoint(item["base_url"], "models"),
                            headers={"Authorization": f"Bearer {item['api_key']}"},
                        )
                    response.raise_for_status()
                    ok = True
                    message = f"HTTP {response.status_code}"
        except Exception as exc:
            message = str(exc)
        if ok:
            await self._apply_model_to_runtime(
                model_type,
                await self._model_repository.get(model_type),
            )
        await self._audit.record(
            "model.tested",
            {"user_id": operator_id, "model_type": model_type, "success": ok},
        )
        return {"model_type": model_type, "success": ok, "message": message}

    async def list_settings(self) -> list[dict[str, Any]]:
        """返回系统参数默认值和覆盖值。"""
        defaults = self._default_settings()
        stored = {item.setting_key: item for item in await self._setting_repository.list_all()}
        result: list[dict[str, Any]] = []
        for key, definition in defaults.items():
            item = stored.get(key)
            value = item.value if item is not None else definition["value"]
            result.append(
                {
                    "setting_key": key,
                    "value": value,
                    "description": item.description if item else definition["description"],
                    "updated_by": item.updated_by if item else "",
                    "updated_at": item.updated_at.isoformat() if item and item.updated_at else "",
                }
            )
        return result

    async def save_setting(
        self, setting_key: str, value: Any, description: str, operator_id: str
    ) -> SystemSetting:
        """保存系统参数。"""
        defaults = self._default_settings()
        if setting_key not in defaults:
            raise ValueError(f"unsupported setting: {setting_key}")
        item = await self._setting_repository.upsert(
            setting_key, value, description or defaults[setting_key]["description"], operator_id
        )
        await self._audit.record(
            "setting.updated",
            {"user_id": operator_id, "setting_key": setting_key, "value": value},
        )
        return item

    # 作用：把当前生效配置写入运行时，停用配置时回退环境默认值。
    async def _apply_model_to_runtime(
        self,
        model_type: str,
        stored: ModelConfig | None,
    ) -> None:
        if self._runtime is None:
            return
        if stored is None or stored.status != "active":
            self._runtime.apply(self._default_resolved_model(model_type))
            self._runtime_applied[model_type] = True
            return
        view = self._to_model_view(model_type, self._default_models()[model_type], stored)
        self._runtime.apply(
            ResolvedModelConfig(
                model_type=model_type,
                base_url=str(view["base_url"]),
                model_name=str(view["model_name"]),
                api_key=self._cipher.decrypt(stored.api_key_ciphertext),
                options=dict(view["options"]),
                status=stored.status,
            )
        )
        self._runtime_applied[model_type] = True

    # 作用：返回环境变量对应的运行时模型配置。
    def _default_resolved_model(self, model_type: str) -> ResolvedModelConfig:
        default = self._default_models()[model_type]
        return ResolvedModelConfig(
            model_type=model_type,
            base_url=str(default["base_url"]),
            model_name=str(default["model_name"]),
            api_key=self._default_api_key(model_type),
            options=dict(default["options"]),
        )

    async def _resolved_model(self, model_type: str) -> dict[str, Any]:
        stored = await self._model_repository.get(model_type)
        default = self._default_models().get(model_type)
        if default is None:
            raise ValueError(f"unsupported model type: {model_type}")
        if stored is None:
            return {**default, "api_key": self._default_api_key(model_type)}
        view = self._to_model_view(model_type, default, stored)
        view["api_key"] = self._cipher.decrypt(stored.api_key_ciphertext)
        return view

    def _to_model_view(
        self, model_type: str, default: dict[str, Any], stored: ModelConfig | None
    ) -> dict[str, Any]:
        if stored is None:
            api_key = self._default_api_key(model_type)
            return {
                **default,
                "config_id": "",
                "status": "active",
                "source": "environment",
                "effective_source": "environment",
                "runtime_applied": self._runtime is not None and self._runtime_applied.get(model_type, False),
                "api_key_masked": self._cipher.mask(api_key),
                "local_model_path": default.get("local_model_path", ""),
            }
        api_key = self._cipher.decrypt(stored.api_key_ciphertext)
        options = {**default.get("options", {}), **(stored.options or {})}
        return {
            "config_id": stored.config_id,
            "model_type": model_type,
            "name": stored.name,
            "base_url": stored.base_url,
            "model_name": stored.model_name,
            "status": stored.status,
            "source": "database",
            "effective_source": "database" if stored.status == "active" else "environment",
            "runtime_applied": self._runtime is not None and self._runtime_applied.get(model_type, False),
            "api_key_masked": self._cipher.mask(api_key),
            "local_model_path": options.get("local_model_path", ""),
            "options": options,
        }

    def _default_models(self) -> dict[str, dict[str, Any]]:
        reranker_url, _, reranker_model, reranker_instruct = self._settings.effective_reranker_config()
        vlm_url, _, vlm_model = self._settings.effective_vlm_config()
        return {
            "llm": {
                "model_type": "llm",
                "name": "默认生成模型",
                "base_url": self._settings.openai_base_url,
                "model_name": self._settings.llm_default_model,
                "options": {
                    "timeout": self._settings.llm_timeout_seconds,
                    "max_tokens": self._settings.llm_max_tokens,
                    "temperature": self._settings.llm_default_temperature,
                    "hyde_temperature": self._settings.llm_hyde_temperature,
                    "hyde_max_tokens": self._settings.llm_hyde_max_tokens,
                },
            },
            "embedding": {
                "model_type": "embedding",
                "name": "默认向量模型",
                "base_url": self._settings.embedding_base_url,
                "model_name": self._settings.bge_m3 or self._settings.embedding_model,
                "local_model_path": self._settings.bge_m3_path,
                "options": {
                    "device": self._settings.bge_device,
                    "fp16": self._settings.bge_fp16,
                    "batch_size": self._settings.embedding_batch_size,
                    "timeout": self._settings.embedding_timeout_seconds,
                    "local_model_name": self._settings.bge_m3,
                    "local_model_path": self._settings.bge_m3_path,
                },
            },
            "reranker": {
                "model_type": "reranker",
                "name": "默认重排模型",
                "base_url": reranker_url,
                "model_name": reranker_model,
                "options": {"instruct": reranker_instruct, "timeout": self._settings.reranker_timeout_seconds},
            },
            "vlm": {
                "model_type": "vlm",
                "name": "默认视觉模型",
                "base_url": vlm_url,
                "model_name": vlm_model,
                "options": {
                    "timeout": self._settings.vlm_timeout_seconds,
                    "max_image_mb": self._settings.vlm_max_image_mb,
                    "confidence_threshold": self._settings.vlm_confidence_threshold,
                    "prompt_version": self._settings.vlm_prompt_version,
                },
            },
        }

    def _default_api_key(self, model_type: str) -> str:
        return {
            "llm": self._settings.openai_api_key,
            "embedding": self._settings.embedding_api_key,
            "reranker": self._settings.effective_reranker_config()[1],
            "vlm": self._settings.effective_vlm_config()[1],
        }.get(model_type, "")

    @staticmethod
    def _model_endpoint(base_url: str, suffix: str) -> str:
        normalized = base_url.rstrip("/")
        if suffix == "rerank" and "/services/rerank/" in normalized:
            return normalized
        return normalized if normalized.endswith(f"/{suffix}") else f"{normalized}/{suffix}"

    def _default_settings(self) -> dict[str, dict[str, Any]]:
        return {
            "context_turns": {"value": 10, "description": "多轮上下文保留轮数"},
            "context_token_limit": {"value": 8192, "description": "上下文 Token 上限"},
            "hybrid_top_k": {"value": self._settings.hybrid_top_k, "description": "混合检索候选数"},
            "reranker_top_k": {"value": self._settings.reranker_top_k, "description": "重排后证据数"},
            "rrf_k": {"value": self._settings.rrf_k, "description": "RRF 平滑参数"},
            "faq_semantic_threshold": {"value": 0.9, "description": "FAQ 语义命中阈值"},
            "faq_fallback_threshold": {"value": 0.8, "description": "FAQ 正常 RAG 回退阈值"},
            "embedding_batch_size": {"value": self._settings.embedding_batch_size, "description": "向量化批大小"},
            "audit_retention_days": {"value": 180, "description": "审计保留天数"},
            "allow_department_descendants": {"value": True, "description": "部门权限允许包含下级"},
        }
