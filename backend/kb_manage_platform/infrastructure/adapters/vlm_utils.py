"""实现基于 LangChain 的 VLM 图片摘要适配器。"""

import base64
import json
import mimetypes
import re
from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from kb_manage_platform.domain.models import ImageSummary
from kb_manage_platform.domain.ports import ObjectStoragePort


class VlmImageSummarizer:
    """读取 MinIO 图片并调用 OpenAI 兼容 VLM 提取结构化摘要。"""

    # 作用：保存图片存储和 VLM 客户端。
    def __init__(
        self,
        storage: ObjectStoragePort,
        image_bucket: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 120,
        max_image_mb: int = 20,
        confidence_threshold: float = 0.75,
        prompt_version: str = "v1",
    ) -> None:
        self._storage = storage
        self._image_bucket = image_bucket
        self._model = model
        self._max_image_bytes = max_image_mb * 1024 * 1024
        self._confidence_threshold = confidence_threshold
        self._prompt_version = prompt_version
        self._llm = self._build_client(
            api_key,
            base_url,
            model,
            timeout_seconds,
        )

    # 作用：在不重启进程的情况下切换 VLM 配置。
    def configure(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 120,
        max_image_mb: int = 20,
        confidence_threshold: float = 0.75,
        prompt_version: str = "v1",
    ) -> None:
        self._model = model
        self._max_image_bytes = max_image_mb * 1024 * 1024
        self._confidence_threshold = confidence_threshold
        self._prompt_version = prompt_version
        self._llm = self._build_client(
            api_key,
            base_url,
            model,
            timeout_seconds,
        )

    # 作用：构造 LangChain OpenAI 兼容客户端。
    @staticmethod
    def _build_client(
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int,
    ) -> ChatOpenAI:
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.0,
            max_tokens=1200,
            timeout=timeout_seconds,
        )

    # 作用：提取图片摘要、OCR 和实体信息。
    async def summarize(self, image_key: str) -> ImageSummary:
        """返回单张图片的结构化理解结果。"""
        content, content_type = await self._load_image(image_key)
        data_url = f"data:{content_type};base64,{base64.b64encode(content).decode('ascii')}"
        response = await self._llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是企业知识库图片理解助手。请提取图片中的关键信息并只输出 JSON，"
                        "字段为 summary、ocr、entities、table_or_chart、confidence。"
                    )
                ),
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "请提取图片摘要，保留关键数字、流程、表格或图表语义。",
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]
                ),
            ]
        )
        payload = self._parse_payload(_message_text(response.content))
        confidence = self._clamp_confidence(payload.get("confidence", 0.0))
        summary = str(payload.get("summary", "")).strip()
        if not summary:
            raise RuntimeError("VLM returned an empty image summary")
        return ImageSummary(
            image_key=image_key,
            summary=summary,
            confidence=confidence,
            model_name=self._model,
            prompt_version=self._prompt_version,
            metadata={
                "ocr": payload.get("ocr", ""),
                "entities": payload.get("entities", []),
                "table_or_chart": payload.get("table_or_chart", ""),
                "accepted": confidence >= self._confidence_threshold,
            },
        )

    # 作用：从 MinIO 或 HTTP 地址读取图片。
    async def _load_image(self, image_key: str) -> tuple[bytes, str]:
        """返回图片字节和 MIME 类型。"""
        if image_key.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=httpx.Timeout(60)) as client:
                response = await client.get(image_key)
                response.raise_for_status()
                content = response.content
                content_type = response.headers.get("content-type", "image/png").split(";", 1)[0]
        else:
            content = await self._storage.get_bytes(self._image_bucket, image_key)
            content_type = mimetypes.guess_type(image_key)[0] or "image/png"
        if len(content) > self._max_image_bytes:
            raise ValueError("image exceeds configured size limit")
        return content, content_type

    # 作用：解析 VLM 返回的 JSON 文本。
    @staticmethod
    def _parse_payload(content: str) -> dict[str, Any]:
        """返回结构化字段，兼容 Markdown JSON 代码块。"""
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            payload = {"summary": content.strip(), "confidence": 0.5}
        return payload if isinstance(payload, dict) else {"summary": str(payload), "confidence": 0.5}

    # 作用：将置信度限制在 0 到 1。
    def _clamp_confidence(self, value: object) -> float:
        """返回规范化置信度。"""
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.0
        return max(0.0, min(1.0, confidence))


# 作用：提取 LangChain 消息中的纯文本。
def _message_text(content: Any) -> str:
    """兼容字符串和内容块列表两种消息格式。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    return str(content or "")