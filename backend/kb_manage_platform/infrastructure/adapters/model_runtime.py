"""将数据库中的模型配置即时应用到运行时适配器。"""

from kb_manage_platform.domain.models import ResolvedModelConfig
from kb_manage_platform.infrastructure.adapters.embedding_utils import ModelEmbedder
from kb_manage_platform.infrastructure.adapters.llm_utils import (
    LangChainAnswerGenerator,
    LangChainHydeGenerator,
)
from kb_manage_platform.infrastructure.adapters.reranker_utils import ModelReranker
from kb_manage_platform.infrastructure.adapters.vlm_utils import VlmImageSummarizer


class ModelRuntimeConfigurator:
    """持有一组运行时模型客户端，并按模型类型更新其连接参数。"""

    def __init__(
        self,
        hyde_generator: LangChainHydeGenerator,
        answer_generator: LangChainAnswerGenerator,
        embedder: ModelEmbedder,
        reranker: ModelReranker,
        image_summarizer: VlmImageSummarizer,
    ) -> None:
        self._hyde_generator = hyde_generator
        self._answer_generator = answer_generator
        self._embedder = embedder
        self._reranker = reranker
        self._image_summarizer = image_summarizer

    # 作用：按模型类型更新问答和入库链路共用的客户端配置。
    def apply(self, config: ResolvedModelConfig) -> None:
        """立即应用模型配置，下一个请求开始使用新参数。"""
        handlers = {
            "llm": self._apply_llm,
            "embedding": self._apply_embedding,
            "reranker": self._apply_reranker,
            "vlm": self._apply_vlm,
        }
        handler = handlers.get(config.model_type)
        if handler is None:
            raise ValueError(f"unsupported model type: {config.model_type}")
        handler(config)

    # 作用：更新回答和 HyDE 两套 LLM 客户端。
    def _apply_llm(self, config: ResolvedModelConfig) -> None:
        options = config.options
        timeout_seconds = self._as_int(options.get("timeout"), 120)
        self._answer_generator.configure(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            temperature=self._as_float(options.get("temperature"), 0.1),
            max_tokens=self._as_int(options.get("max_tokens"), 2048),
            timeout_seconds=timeout_seconds,
        )
        self._hyde_generator.configure(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            temperature=self._as_float(options.get("hyde_temperature"), 0.1),
            max_tokens=self._as_int(options.get("hyde_max_tokens"), 512),
            timeout_seconds=timeout_seconds,
        )

    # 作用：更新本地或远程 Embedding 客户端。
    def _apply_embedding(self, config: ResolvedModelConfig) -> None:
        options = config.options
        local_model_path = self._as_str(options.get("local_model_path"))
        local_model_name = self._as_str(options.get("local_model_name"))
        if not local_model_name and local_model_path:
            local_model_name = config.model_name
        self._embedder.configure(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model_name,
            batch_size=self._as_int(options.get("batch_size"), 32),
            timeout_seconds=self._as_int(options.get("timeout"), 60),
            local_model_name=local_model_name,
            local_model_path=local_model_path,
            device=self._as_str(options.get("device")) or "cpu",
            use_fp16=self._as_bool(options.get("fp16")),
        )

    # 作用：更新 Reranker 客户端。
    def _apply_reranker(self, config: ResolvedModelConfig) -> None:
        options = config.options
        self._reranker.configure(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model_name,
            instruct=self._as_str(options.get("instruct")),
            timeout_seconds=self._as_int(options.get("timeout"), 60),
        )

    # 作用：更新图片理解 VLM 客户端。
    def _apply_vlm(self, config: ResolvedModelConfig) -> None:
        options = config.options
        self._image_summarizer.configure(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model_name,
            timeout_seconds=self._as_int(options.get("timeout"), 120),
            max_image_mb=self._as_int(options.get("max_image_mb"), 20),
            confidence_threshold=self._as_float(options.get("confidence_threshold"), 0.75),
            prompt_version=self._as_str(options.get("prompt_version")) or "v1",
        )

    @staticmethod
    def _as_int(value: object, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_float(value: object, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @staticmethod
    def _as_str(value: object) -> str:
        return str(value).strip() if value is not None else ""