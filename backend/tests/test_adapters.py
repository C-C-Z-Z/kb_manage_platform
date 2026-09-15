"""验证新增外部适配器的纯逻辑与存储转换。"""

from io import BytesIO
from zipfile import ZipFile

import pytest

from kb_manage_platform.bootstrap.settings import Settings
from kb_manage_platform.domain.models import ImageSummary
from kb_manage_platform.infrastructure.adapters.chunk_utils import BasicChunker
from kb_manage_platform.infrastructure.adapters.embedding_utils import ModelEmbedder
from kb_manage_platform.infrastructure.adapters.milvus_utils import MilvusStore
from kb_manage_platform.infrastructure.adapters.mineru_utils import MineruDocumentParser
from kb_manage_platform.infrastructure.adapters.reranker_utils import ModelReranker


class FakeStorage:
    """内存对象存储测试桩。"""

    # 作用：初始化对象和调用记录。
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.calls: list[tuple[str, str, str]] = []

    # 作用：读取对象。
    async def get_bytes(self, bucket: str, object_key: str) -> bytes:
        """返回预置对象。"""
        return self.objects[(bucket, object_key)]

    # 作用：写入对象。
    async def put_bytes(self, bucket: str, object_key: str, content: bytes, content_type: str) -> str:
        """保存对象并记录调用。"""
        self.objects[(bucket, object_key)] = content
        self.calls.append((bucket, object_key, content_type))
        return object_key


# 作用：验证切片器替换图片摘要。
@pytest.mark.asyncio
async def test_chunker_uses_image_summary() -> None:
    """图片摘要应进入对应知识切片。"""
    chunker = BasicChunker()
    chunks = await chunker.chunk(
        markdown="# 安装\n\n请参考下图。\n\n![示意图](images/step.png)",
        images=[
            ImageSummary(
                image_key="uploads/images/step.png",
                summary="图中展示先安装底座，再固定面板。",
                confidence=0.9,
                model_name="test-vlm",
                prompt_version="v1",
                metadata={"source_path": "images/step.png", "accepted": True},
            )
        ],
        knowledge_id="k1",
        version_id="v1",
    )
    assert len(chunks) == 1
    assert "先安装底座" in chunks[0].content
    assert chunks[0].section_path == "安装"


# 作用：验证 TXT 文件转换为 Markdown 并写入对象存储。
@pytest.mark.asyncio
async def test_mineru_text_conversion() -> None:
    """TXT 无需调用 MinerU API，应直接转换为 Markdown。"""
    storage = FakeStorage()
    storage.objects[("raw", "docs/a.txt")] = "第一段\n\n第二段".encode()
    parser = MineruDocumentParser(
        storage=storage,
        api_token="",
        base_url="https://mineru.net/api/v4",
        raw_bucket="raw",
        markdown_bucket="markdown",
        image_bucket="images",
    )
    markdown, images = await parser.parse("docs/a.txt", "a.txt")
    assert markdown.startswith("# a")
    assert images == []
    assert ("markdown", "docs/document.md") in storage.objects


# 作用：验证 MinerU ZIP 提取。
def test_mineru_extract_archive() -> None:
    """应从 ZIP 中选择 full.md 并提取图片。"""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("full.md", "# 标题")
        archive.writestr("images/a.png", b"png")
    parser = MineruDocumentParser(
        storage=FakeStorage(),
        api_token="token",
        base_url="https://mineru.net/api/v4",
        raw_bucket="raw",
        markdown_bucket="markdown",
        image_bucket="images",
    )
    markdown, images = parser._extract_archive(buffer.getvalue())
    assert markdown == "# 标题"
    assert images == [("images/a.png", b"png")]


# 作用：验证 Settings 优先读取 env.txt 字段。
def test_settings_env_txt_aliases() -> None:
    """有效别名应转换为统一配置。"""
    settings = Settings(
        _env_file=None,
        minio_bucket_name="knowledge-base",
        minio_img_dir="upload-images",
        milvus_url="http://milvus:19530",
        chunks_collection="kb_chunks",
        vl_model="qwen3-vl-flash",
        text_rerank_base_url="https://rerank.example/v1",
        text_rerank_model="qwen3-rerank",
    )
    assert settings.effective_minio_bucket("raw") == "knowledge-base"
    assert settings.effective_image_prefix() == "upload-images"
    assert settings.effective_milvus_uri() == "http://milvus:19530"
    assert settings.effective_milvus_collection() == "kb_chunks"
    assert settings.effective_vlm_config()[2] == "qwen3-vl-flash"


# 作用：验证 Milvus 返回结构转换。
def test_milvus_result_conversion() -> None:
    """Milvus 候选应转换为领域对象。"""
    results = [[{
        "id": "c1",
        "distance": 0.9,
        "entity": {
            "chunk_id": "c1",
            "knowledge_id": "k1",
            "version_id": "v1",
            "content": "正文",
            "section_path": "章节",
            "image_summary": "",
        },
    }]]
    candidates = MilvusStore._to_candidates(results, "hybrid")
    assert candidates[0].chunk_id == "c1"
    assert candidates[0].source == "hybrid"


# 作用：验证 Reranker 响应解析。
def test_reranker_response_parsing() -> None:
    """兼容 output.results 响应结构。"""
    results = ModelReranker._extract_results({"output": {"results": [{"index": 0, "relevance_score": 1.0}]}})
    assert results[0]["index"] == 0

# 作用：验证同时配置远程与本地模型时优先使用本地 BGE-M3。
@pytest.mark.asyncio
async def test_embedder_prefers_local_bge(monkeypatch: pytest.MonkeyPatch) -> None:
    """本地方案存在时不应误走远程 Embedding。"""
    embedder = ModelEmbedder(
        base_url="https://api.example.com/v1",
        api_key="key",
        model="remote-embedding",
        local_model_name="BAAI/bge-m3",
        local_model_path="D:/models/bge-m3",
    )

    # 作用：记录本地分支调用。
    async def fake_local(texts):
        """返回固定向量。"""
        return [[1.0, 0.0] for _ in texts]

    # 作用：远程分支被调用时直接失败。
    async def fake_remote(texts):
        """阻止远程回退。"""
        raise AssertionError("remote embedding should not be used")

    monkeypatch.setattr(embedder, "_embed_local", fake_local)
    monkeypatch.setattr(embedder, "_embed_remote", fake_remote)
    vectors = await embedder.embed(["test"])
    assert vectors == [[1.0, 0.0]]

@pytest.mark.asyncio
async def test_mineru_presigned_upload_omits_content_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """MinerU 预签名上传地址不接受 Content-Type，否则会触发签名不匹配。"""
    from kb_manage_platform.infrastructure.adapters import mineru_utils

    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def put(self, url, content, headers=None):
            captured["headers"] = headers
            captured["content"] = content
            return FakeResponse()

    monkeypatch.setattr(mineru_utils.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    parser = MineruDocumentParser(
        storage=None,  # type: ignore[arg-type]
        api_token="token",
        base_url="https://mineru.net/api/v4",
        raw_bucket="raw",
        markdown_bucket="markdown",
        image_bucket="images",
    )

    await parser._upload_file("https://example-upload", "a.docx", b"docx")

    assert captured["headers"] is None
    assert captured["content"] == b"docx"