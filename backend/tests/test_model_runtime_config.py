"""验证模型配置能够即时进入运行时链路。"""

import pytest

from kb_manage_platform.bootstrap.settings import Settings
from kb_manage_platform.domain.models import ModelConfig, ResolvedModelConfig
from kb_manage_platform.infrastructure.adapters.model_runtime import ModelRuntimeConfigurator
from kb_manage_platform.infrastructure.adapters.secret_utils import LocalSecretCipher
from kb_manage_platform.services.configuration_service import ConfigurationService


class FakeAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def configure(self, **kwargs) -> None:
        self.calls.append(kwargs)


class FakeAudit:
    async def record(self, event_type: str, payload: dict[str, object]) -> None:
        return None


class FakeSettingRepository:
    async def list_all(self):
        return ()

    async def upsert(self, setting_key, value, description, operator_id):
        raise AssertionError("not used")


class FakeModelRepository:
    def __init__(self, stored: tuple[ModelConfig, ...] = ()) -> None:
        self._stored = {item.model_type: item for item in stored}

    async def list_all(self):
        return tuple(self._stored.values())

    async def get(self, model_type: str):
        return self._stored.get(model_type)

    async def upsert(
        self,
        model_type,
        name,
        base_url,
        model_name,
        api_key_ciphertext,
        options,
        status,
        operator_id,
    ):
        item = ModelConfig(
            config_id=f"config-{model_type}",
            model_type=model_type,
            name=name,
            base_url=base_url,
            model_name=model_name,
            api_key_ciphertext=api_key_ciphertext,
            options=dict(options),
            status=status,
            updated_by=operator_id,
        )
        self._stored[model_type] = item
        return item


class FakeRuntime:
    def __init__(self) -> None:
        self.applied: list[ResolvedModelConfig] = []

    def apply(self, config: ResolvedModelConfig) -> None:
        self.applied.append(config)


def make_service(
    repository: FakeModelRepository,
    runtime: FakeRuntime | None = None,
) -> ConfigurationService:
    settings = Settings(
        openai_base_url="https://env.example/v1",
        openai_api_key="env-llm-key",
        llm_default_model="env-llm",
        embedding_base_url="https://env.example/v1",
        embedding_api_key="env-embedding-key",
        embedding_model="env-embedding",
        reranker_model="env-reranker",
        reranker_api_key="env-reranker-key",
        vlm_model="env-vlm",
        vlm_api_key="env-vlm-key",
    )
    return ConfigurationService(
        settings,
        repository,
        FakeSettingRepository(),
        LocalSecretCipher("test-secret"),
        FakeAudit(),
        runtime,
    )


def test_runtime_configurator_applies_all_model_types() -> None:
    hyde = FakeAdapter()
    answer = FakeAdapter()
    embedder = FakeAdapter()
    reranker = FakeAdapter()
    vlm = FakeAdapter()
    runtime = ModelRuntimeConfigurator(
        hyde_generator=hyde,  # type: ignore[arg-type]
        answer_generator=answer,  # type: ignore[arg-type]
        embedder=embedder,  # type: ignore[arg-type]
        reranker=reranker,  # type: ignore[arg-type]
        image_summarizer=vlm,  # type: ignore[arg-type]
    )

    runtime.apply(
        ResolvedModelConfig(
            model_type="llm",
            base_url="https://llm.example/v1",
            model_name="llm-new",
            api_key="llm-key",
            options={
                "temperature": 0.2,
                "max_tokens": 100,
                "hyde_temperature": 0.3,
                "hyde_max_tokens": 50,
                "timeout": 30,
            },
        )
    )
    runtime.apply(
        ResolvedModelConfig(
            model_type="embedding",
            base_url="https://embedding.example/v1",
            model_name="embedding-new",
            api_key="embedding-key",
            options={"batch_size": 8, "timeout": 20},
        )
    )
    runtime.apply(
        ResolvedModelConfig(
            model_type="reranker",
            base_url="https://reranker.example/v1",
            model_name="reranker-new",
            api_key="reranker-key",
            options={"timeout": 10, "instruct": "rank"},
        )
    )
    runtime.apply(
        ResolvedModelConfig(
            model_type="vlm",
            base_url="https://vlm.example/v1",
            model_name="vlm-new",
            api_key="vlm-key",
            options={"timeout": 40, "max_image_mb": 5},
        )
    )

    assert answer.calls[0]["model"] == "llm-new"
    assert hyde.calls[0]["model"] == "llm-new"
    assert embedder.calls[0]["model"] == "embedding-new"
    assert reranker.calls[0]["model"] == "reranker-new"
    assert vlm.calls[0]["model"] == "vlm-new"


@pytest.mark.asyncio
async def test_save_model_applies_runtime_immediately() -> None:
    repository = FakeModelRepository()
    runtime = FakeRuntime()
    service = make_service(repository, runtime)

    saved = await service.save_model(
        "llm",
        "生产模型",
        "https://new.example/v1",
        "new-model",
        "new-secret",
        {
            "temperature": 0.2,
            "max_tokens": 100,
            "timeout": 30,
            "hyde_temperature": 0.1,
            "hyde_max_tokens": 50,
        },
        "active",
        "admin",
    )

    assert runtime.applied[-1].model_type == "llm"
    assert runtime.applied[-1].base_url == "https://new.example/v1"
    assert runtime.applied[-1].model_name == "new-model"
    assert runtime.applied[-1].api_key == "new-secret"
    assert saved["runtime_applied"] is True


@pytest.mark.asyncio
async def test_initialize_runtime_loads_database_override() -> None:
    cipher = LocalSecretCipher("test-secret")
    stored = ModelConfig(
        config_id="config-embedding",
        model_type="embedding",
        name="数据库向量模型",
        base_url="https://db-embedding.example/v1",
        model_name="db-embedding",
        api_key_ciphertext=cipher.encrypt("db-key"),
        options={"batch_size": 4},
        status="active",
    )
    runtime = FakeRuntime()
    service = make_service(FakeModelRepository((stored,)), runtime)

    await service.initialize_runtime()

    embedding = next(item for item in runtime.applied if item.model_type == "embedding")
    assert embedding.base_url == "https://db-embedding.example/v1"
    assert embedding.model_name == "db-embedding"
    assert embedding.api_key == "db-key"


@pytest.mark.asyncio
async def test_disabled_database_model_falls_back_to_environment() -> None:
    cipher = LocalSecretCipher("test-secret")
    stored = ModelConfig(
        config_id="config-llm",
        model_type="llm",
        name="停用模型",
        base_url="https://disabled.example/v1",
        model_name="disabled-model",
        api_key_ciphertext=cipher.encrypt("disabled-key"),
        options={},
        status="disabled",
    )
    runtime = FakeRuntime()
    service = make_service(FakeModelRepository((stored,)), runtime)

    await service.initialize_runtime()

    llm = next(item for item in runtime.applied if item.model_type == "llm")
    assert llm.base_url == "https://env.example/v1"
    assert llm.model_name == "env-llm"
    assert llm.api_key == "env-llm-key"