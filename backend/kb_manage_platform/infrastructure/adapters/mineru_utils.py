"""实现线上 MinerU API 文档解析适配器。"""

import asyncio
import mimetypes
from collections.abc import Sequence
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

import httpx

from kb_manage_platform.domain.ports import ObjectStoragePort


class MineruDocumentParser:
    """调用线上 MinerU，将 PDF/Word 转换为 Markdown 并抽取图片。"""

    _TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
    _MINERU_SUFFIXES = {".pdf", ".doc", ".docx"}
    _IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg"}

    # 作用：保存对象存储、线上 MinerU 参数和桶配置。
    def __init__(
        self,
        storage: ObjectStoragePort,
        api_token: str,
        base_url: str,
        raw_bucket: str,
        markdown_bucket: str,
        image_bucket: str,
        image_prefix: str = "",
        timeout_seconds: int = 600,
        poll_interval_seconds: int = 3,
        max_file_mb: int = 100,
    ) -> None:
        self._storage = storage
        self._api_token = api_token.strip()
        self._base_url = base_url.rstrip("/")
        self._raw_bucket = raw_bucket
        self._markdown_bucket = markdown_bucket
        self._image_bucket = image_bucket
        self._image_prefix = image_prefix.strip().strip("/")
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = max(1, poll_interval_seconds)
        self._max_file_bytes = max_file_mb * 1024 * 1024

    # 作用：解析原始文档并返回 Markdown 与图片对象键。
    async def parse(self, object_key: str, filename: str) -> tuple[str, Sequence[str]]:
        """解析文本、PDF 或 Word 文档。"""
        suffix = PurePosixPath(filename).suffix.lower()
        content = await self._storage.get_bytes(self._raw_bucket, object_key)
        if len(content) > self._max_file_bytes:
            raise ValueError(f"document exceeds {self._max_file_bytes // 1024 // 1024} MB")
        if suffix in self._TEXT_SUFFIXES:
            return await self._store_text_document(object_key, filename, content, suffix)
        if suffix not in self._MINERU_SUFFIXES:
            raise ValueError(f"unsupported document type: {suffix}")
        self._validate_api_config()
        batch_id, upload_url = await self._request_upload_url(filename)
        await self._upload_file(upload_url, filename, content)
        archive_url = await self._wait_for_result(batch_id)
        archive = await self._download_archive(archive_url)
        markdown, images = await asyncio.to_thread(self._extract_archive, archive)
        image_keys = await self._store_images(object_key, images)
        markdown_key = self._build_markdown_key(object_key)
        await self._storage.put_bytes(
            self._markdown_bucket,
            markdown_key,
            markdown.encode("utf-8"),
            "text/markdown; charset=utf-8",
        )
        return markdown, image_keys

    # 作用：将 Markdown 或 TXT 原文规范化后写入 Markdown 桶。
    async def _store_text_document(
        self,
        object_key: str,
        filename: str,
        content: bytes,
        suffix: str,
    ) -> tuple[str, Sequence[str]]:
        """保存文本文档并返回 Markdown。"""
        markdown = content.decode("utf-8-sig", errors="replace")
        if suffix == ".txt":
            title = PurePosixPath(filename).stem or "document"
            markdown = f"# {title}\n\n{markdown}"
        await self._storage.put_bytes(
            self._markdown_bucket,
            self._build_markdown_key(object_key),
            markdown.encode("utf-8"),
            "text/markdown; charset=utf-8",
        )
        return markdown, []

    # 作用：申请 MinerU 文件上传地址。
    async def _request_upload_url(self, filename: str) -> tuple[str, str]:
        """创建一个批处理任务并返回 batch ID 与签名上传地址。"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
            response = await client.post(
                f"{self._base_url}/file-urls/batch",
                headers=self._headers(),
                json={"files": [{"name": filename}], "model_version": "vlm"},
            )
            response.raise_for_status()
            payload = response.json()
        self._ensure_success(payload, "create MinerU upload url")
        data = payload.get("data", {})
        file_urls = data.get("file_urls", [])
        if not data.get("batch_id") or not file_urls:
            raise RuntimeError("MinerU did not return batch_id or file_urls")
        return str(data["batch_id"]), str(file_urls[0])

    # 作用：将原始文件上传到 MinerU 返回的签名地址。
    async def _upload_file(self, upload_url: str, filename: str, content: bytes) -> None:
        """上传原始文件字节。"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout_seconds)) as client:
            response = await client.put(upload_url, content=content)
            response.raise_for_status()

    # 作用：轮询线上解析任务直到完成或超时。
    async def _wait_for_result(self, batch_id: str) -> str:
        """返回 MinerU 结果 ZIP 下载地址。"""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout_seconds
        while loop.time() < deadline:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(20)) as client:
                    response = await client.get(
                        f"{self._base_url}/extract-results/batch/{batch_id}",
                        headers=self._headers(),
                    )
                    response.raise_for_status()
                    payload = response.json()
            except httpx.HTTPError:
                await asyncio.sleep(self._poll_interval_seconds)
                continue
            self._ensure_success(payload, "poll MinerU result")
            results = payload.get("data", {}).get("extract_result", [])
            if not results:
                await asyncio.sleep(self._poll_interval_seconds)
                continue
            result = results[0]
            state = str(result.get("state", "")).lower()
            if state == "done":
                archive_url = str(result.get("full_zip_url", "")).strip()
                if not archive_url:
                    raise RuntimeError("MinerU completed without full_zip_url")
                return archive_url
            if state == "failed":
                raise RuntimeError(f"MinerU parsing failed: {result.get('err_msg', 'unknown error')}")
            await asyncio.sleep(self._poll_interval_seconds)
        raise TimeoutError(f"MinerU parsing timed out after {self._timeout_seconds} seconds")

    # 作用：下载 MinerU 结果 ZIP。
    async def _download_archive(self, archive_url: str) -> bytes:
        """返回结果压缩包字节。"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout_seconds)) as client:
            response = await client.get(archive_url)
            response.raise_for_status()
            return response.content

    # 作用：在内存中安全解压 full.md 和图片资源。
    def _extract_archive(self, archive: bytes) -> tuple[str, list[tuple[str, bytes]]]:
        """返回 Markdown 正文和图片文件列表。"""
        try:
            with ZipFile(BytesIO(archive)) as zip_file:
                names = [name for name in zip_file.namelist() if not name.endswith("/")]
                markdown_name = self._select_markdown(names)
                markdown = zip_file.read(markdown_name).decode("utf-8-sig", errors="replace")
                images = [
                    (name, zip_file.read(name))
                    for name in names
                    if PurePosixPath(name).suffix.lower() in self._IMAGE_SUFFIXES
                ]
        except BadZipFile as exc:
            raise RuntimeError("MinerU result is not a valid ZIP archive") from exc
        if not markdown.strip():
            raise RuntimeError("MinerU returned an empty Markdown document")
        return markdown, images

    # 作用：保存 MinerU 提取出的全部图片。
    async def _store_images(
        self,
        object_key: str,
        images: Sequence[tuple[str, bytes]],
    ) -> list[str]:
        """返回写入 MinIO 的图片对象键。"""
        image_keys: list[str] = []
        for source_name, content in images:
            relative_name = self._safe_relative_path(source_name)
            image_key = self._build_image_key(object_key, relative_name)
            content_type = mimetypes.guess_type(relative_name)[0] or "application/octet-stream"
            await self._storage.put_bytes(
                self._image_bucket,
                image_key,
                content,
                content_type,
            )
            image_keys.append(image_key)
        return image_keys

    # 作用：选择结果中的主 Markdown 文件。
    @staticmethod
    def _select_markdown(names: Sequence[str]) -> str:
        """优先选择 full.md，否则选择首个 Markdown 文件。"""
        markdown_files = [name for name in names if PurePosixPath(name).suffix.lower() == ".md"]
        if not markdown_files:
            raise RuntimeError("MinerU result does not contain a Markdown file")
        for name in markdown_files:
            if PurePosixPath(name).name.lower() == "full.md":
                return name
        return markdown_files[0]

    # 作用：移除 ZIP 中的绝对路径和目录穿越片段。
    @staticmethod
    def _safe_relative_path(name: str) -> str:
        """返回安全相对路径。"""
        parts = [part for part in PurePosixPath(name).parts if part not in {"", ".", "..", "/"}]
        return PurePosixPath(*parts).as_posix()

    # 作用：构造 Markdown 对象键。
    @staticmethod
    def _build_markdown_key(object_key: str) -> str:
        """返回原始对象同目录下的 document.md。"""
        source = PurePosixPath(object_key)
        return (source.parent / "document.md").as_posix()

    # 作用：构造图片对象键。
    def _build_image_key(self, object_key: str, relative_name: str) -> str:
        """返回统一图片目录下的对象键。"""
        source = PurePosixPath(object_key)
        prefix = self._image_prefix or f"{source.parent.as_posix()}/images"
        return f"{prefix.strip('/')}/{relative_name.lstrip('/')}"

    # 作用：校验 MinerU 线上 API 配置。
    def _validate_api_config(self) -> None:
        """阻止使用空 Token 或占位地址调用线上服务。"""
        if not self._api_token or self._api_token.upper().startswith("CHANGE_ME"):
            raise RuntimeError("MINERU_API_TOKEN is not configured")
        if not self._base_url or "example.com" in self._base_url:
            raise RuntimeError("MINERU_BASE_URL is not configured")

    # 作用：返回 MinerU 请求头。
    def _headers(self) -> dict[str, str]:
        """返回带 Bearer Token 的请求头。"""
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

    # 作用：校验 MinerU 响应业务码。
    @staticmethod
    def _ensure_success(payload: dict[str, object], action: str) -> None:
        """在业务码非零时抛出异常。"""
        if int(payload.get("code", -1)) != 0:
            raise RuntimeError(f"{action} failed: {payload.get('msg', 'unknown error')}")