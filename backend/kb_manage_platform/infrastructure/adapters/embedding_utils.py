"""实现远程 OpenAI Embedding 与本地 BGE-M3 两种向量化适配器。"""

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx


class ModelEmbedder:
    """优先使用本地 BGE-M3，也可切换为远程 OpenAI Embedding 接口。"""

    # 作用：保存远程接口和本地 BGE 模型参数。
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        batch_size: int = 32,
        timeout_seconds: int = 60,
        local_model_name: str = "",
        local_model_path: str = "",
        device: str = "cpu",
        use_fp16: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._batch_size = max(1, batch_size)
        self._timeout_seconds = timeout_seconds
        self._local_model_name = local_model_name.strip()
        self._local_model_path = local_model_path.strip()
        self._device = device
        self._use_fp16 = use_fp16
        self._local_model: Any = None
        self._local_model_lock = asyncio.Lock()

    # 作用：在不重启进程的情况下切换 Embedding 配置。
    def configure(
        self,
        base_url: str,
        api_key: str,
        model: str,
        batch_size: int = 32,
        timeout_seconds: int = 60,
        local_model_name: str = "",
        local_model_path: str = "",
        device: str = "cpu",
        use_fp16: bool = False,
    ) -> None:
        local_model_name = local_model_name.strip()
        local_model_path = local_model_path.strip()
        local_locator_changed = (
            local_model_name != self._local_model_name
            or local_model_path != self._local_model_path
            or device != self._device
            or use_fp16 != self._use_fp16
        )
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._batch_size = max(1, batch_size)
        self._timeout_seconds = timeout_seconds
        self._local_model_name = local_model_name
        self._local_model_path = local_model_path
        self._device = device
        self._use_fp16 = use_fp16
        if local_locator_changed:
            self._local_model = None

    # 作用：批量生成文本向量。
    async def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """返回与输入等长的向量列表。"""
        if not texts:
            return []
        self._validate_config()
        if self._local_model_path or self._local_model_name:
            return await self._embed_local(texts)
        return await self._embed_remote(texts)

    # 作用：校验至少配置一种 Embedding 后端。
    def _validate_config(self) -> None:
        """阻止在无模型配置时继续执行。"""
        remote_ready = self._configured(self._base_url) and self._configured(self._model)
        local_ready = bool(self._local_model_path or self._local_model_name)
        if not remote_ready and not local_ready:
            raise RuntimeError("embedding model is not configured")

    # 作用：按批次调用远程 Embedding 接口。
    async def _embed_remote(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """返回远程模型向量。"""
        vectors: list[list[float]] = []
        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for start in range(0, len(texts), self._batch_size):
                batch = list(texts[start : start + self._batch_size])
                vectors.extend(await self._embed_batch(client, batch))
        return vectors

    # 作用：执行一个远程批次请求。
    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        batch: Sequence[str],
    ) -> list[list[float]]:
        """返回单批文本向量。"""
        response = await client.post(
            f"{self._base_url}/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "input": list(batch)},
        )
        response.raise_for_status()
        payload = response.json()
        rows = sorted(payload.get("data", []), key=lambda item: int(item.get("index", 0)))
        vectors = [list(item["embedding"]) for item in rows]
        if len(vectors) != len(batch):
            raise RuntimeError("embedding response size does not match input")
        return vectors

    # 作用：使用本地 BGE-M3 生成向量。
    async def _embed_local(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """返回本地 SentenceTransformer 向量。"""
        model = await self._get_local_model()
        vectors = await asyncio.to_thread(
            model.encode,
            list(texts),
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return [vector.tolist() for vector in vectors]

    # 作用：延迟加载本地 BGE-M3 模型。
    async def _get_local_model(self) -> Any:
        """返回线程安全缓存的本地模型。"""
        async with self._local_model_lock:
            if self._local_model is not None:
                return self._local_model
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "local embedding requires the optional sentence-transformers dependency"
                ) from exc
            path = self._local_model_path
            if not path or not Path(path).exists():
                path = self._local_model_name
            if not path:
                raise RuntimeError("local BGE-M3 model path or name is not configured")
            model = await asyncio.to_thread(SentenceTransformer, path, device=self._device)
            if self._use_fp16:
                model.half()
            self._local_model = model
            return model

    # 作用：判断配置值是否有效。
    @staticmethod
    def _configured(value: str) -> bool:
        """返回配置值是否非空且不是占位符。"""
        return bool(value.strip()) and not value.strip().upper().startswith("CHANGE_ME")