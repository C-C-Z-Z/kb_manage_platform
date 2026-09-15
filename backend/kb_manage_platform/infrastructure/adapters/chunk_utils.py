"""实现 Markdown 标题感知切片适配器。"""

import re
from collections.abc import Sequence
from pathlib import PurePosixPath
from uuid import NAMESPACE_URL, uuid5

from kb_manage_platform.domain.models import ImageSummary, KnowledgeChunk


class BasicChunker:
    """按 Markdown 标题和段落生成可检索知识切片。"""

    _HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
    _IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

    # 作用：保存最大切片长度和重叠长度。
    def __init__(self, max_chars: int = 1200, overlap_chars: int = 150) -> None:
        self._max_chars = max(200, max_chars)
        self._overlap_chars = max(0, min(overlap_chars, self._max_chars // 2))

    # 作用：按正文和图片摘要生成知识切片。
    async def chunk(
        self,
        markdown: str,
        images: Sequence[ImageSummary],
        knowledge_id: str,
        version_id: str,
    ) -> Sequence[KnowledgeChunk]:
        """返回带稳定 ID 的知识切片。"""
        sections = self._split_sections(markdown)
        chunks: list[KnowledgeChunk] = []
        for section_path, section_text in sections:
            normalized, summaries = self._replace_images(section_text, images)
            for content in self._split_content(normalized):
                chunk_index = len(chunks)
                chunk_id = str(uuid5(NAMESPACE_URL, f"{knowledge_id}:{version_id}:{section_path}:{chunk_index}"))
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=chunk_id,
                        knowledge_id=knowledge_id,
                        version_id=version_id,
                        content=content,
                        section_path=section_path,
                        image_summary="\n".join(summaries),
                    )
                )
        return chunks

    # 作用：将图片 Markdown 替换为 VLM 摘要。
    def _replace_images(
        self,
        content: str,
        images: Sequence[ImageSummary],
    ) -> tuple[str, list[str]]:
        """返回替换后的正文和命中的图片摘要。"""
        summary_by_name = {
            PurePosixPath(str(image.metadata.get("source_path", "")) or image.image_key).name: image.summary
            for image in images
            if image.summary.strip()
        }

        # 作用：按图片引用路径匹配对应摘要。
        def replace(match: re.Match[str]) -> str:
            """返回图片引用的摘要文本。"""
            source = match.group(1).strip().strip("<>").split("?", 1)[0]
            name = PurePosixPath(source).name
            summary = summary_by_name.get(name)
            if not summary:
                return match.group(0)
            return f"\n> 图片摘要：{summary}\n"

        normalized = self._IMAGE_PATTERN.sub(replace, content)
        matched = [
            summary
            for name, summary in summary_by_name.items()
            if name in content or summary in normalized
        ]
        return normalized, list(dict.fromkeys(matched))

    # 作用：按 Markdown 标题拆分为章节。
    def _split_sections(self, markdown: str) -> list[tuple[str, str]]:
        """返回章节路径和正文。"""
        text = markdown.replace("\r\n", "\n").strip()
        if not text:
            return []
        matches = list(self._HEADING_PATTERN.finditer(text))
        if not matches:
            return [("正文", text)]
        sections: list[tuple[str, str]] = []
        heading_stack: list[tuple[int, str]] = []
        if matches[0].start() > 0:
            sections.append(("正文", text[: matches[0].start()].strip()))
        for index, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack = [(item_level, item_title) for item_level, item_title in heading_stack if item_level < level]
            heading_stack.append((level, title))
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[match.end() : end].strip()
            section_path = " / ".join(item_title for _, item_title in heading_stack)
            sections.append((section_path, body))
        return [(path, body) for path, body in sections if body]

    # 作用：按段落和字符窗口切分单个章节。
    def _split_content(self, content: str) -> list[str]:
        """返回长度受控的正文切片。"""
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
        if not paragraphs:
            return []
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if not current:
                current = paragraph
                continue
            candidate = f"{current}\n\n{paragraph}"
            if len(candidate) <= self._max_chars:
                current = candidate
                continue
            chunks.append(current)
            overlap = current[-self._overlap_chars :] if self._overlap_chars else ""
            current = f"{overlap}\n\n{paragraph}".strip()
        if current:
            chunks.append(current)
        return chunks