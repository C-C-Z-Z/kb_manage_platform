"""实现 VLM 图片摘要节点。"""

from typing import Any

from kb_manage_platform.common.logger import logger
from kb_manage_platform.domain.models import ImageSummary
from kb_manage_platform.domain.ports import ImageSummarizerPort
from kb_manage_platform.engines.ingestion_engine.base import ImportNodeBase
from kb_manage_platform.engines.ingestion_engine.state import IngestionGraphState


class NodeVlmSummary(ImportNodeBase):
    """调用 VLM 提取图片信息并生成摘要。"""

    name = "node_vlm_summary"

    # 作用：保存 VLM 图片摘要端口。
    def __init__(self, summarizer: ImageSummarizerPort) -> None:
        self._summarizer = summarizer

    # 作用：逐张生成图片摘要，单图失败不阻塞整篇文档。
    async def process(self, state: IngestionGraphState) -> dict[str, Any]:
        """返回结构化图片摘要。"""
        summaries: list[ImageSummary] = []
        for image_key in state.get("image_keys", []):
            try:
                summaries.append(await self._summarizer.summarize(image_key))
            except Exception as exc:
                logger.warning("VLM image summary failed for %s: %s", image_key, exc)
                summaries.append(
                    ImageSummary(
                        image_key=image_key,
                        summary="",
                        confidence=0.0,
                        model_name="unavailable",
                        prompt_version="",
                        metadata={"error": str(exc), "accepted": False},
                    )
                )
        return {"image_summaries": summaries}