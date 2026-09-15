"""集中读取应用、数据库、缓存、存储、检索和模型相关环境参数。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用运行参数。具体连接和调用由基础设施适配器负责。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "kb-manage-platform"
    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"
    app_workers: int = 1
    app_api_prefix: str = "/api/v1"
    app_sse_heartbeat_seconds: int = 15
    app_sse_timeout_seconds: int = 300
    cors_origins: str = "http://localhost:5173"
    jwt_secret_key: str = "CHANGE_ME_JWT_SECRET"
    jwt_expires_seconds: int = 28800
    jwt_issuer: str = "kb-manage-platform"
    password_lock_threshold: int = 5
    password_lock_seconds: int = 900
    seed_admin_username: str = "admin"
    seed_admin_password: str = "CHANGE_ME_ADMIN_PASSWORD"
    seed_demo_data: bool = False

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_database: str = "kb_manage"
    mysql_user: str = "kb_app"
    mysql_password: str = "CHANGE_ME"
    mysql_charset: str = "utf8mb4"
    mysql_pool_size: int = 10
    mysql_job_poll_interval_seconds: int = 2
    mysql_job_batch_size: int = 10
    mysql_job_lock_timeout_seconds: int = 300
    mysql_job_max_attempts: int = 3
    scheduler_poll_interval_seconds: int = 30
    scheduler_enabled: bool = True
    scheduler_faq_mining_interval_seconds: int = 86400
    scheduler_faq_mining_window_days: int = 30
    scheduler_gap_detection_interval_seconds: int = 86400
    scheduler_gap_detection_window_days: int = 30
    scheduler_operator_id: str = "system-scheduler"
    model_config_refresh_interval_seconds: int = 10

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = "CHANGE_ME"
    redis_cache_ttl_seconds: int = 3600
    redis_permission_ttl_seconds: int = 300
    redis_lock_ttl_seconds: int = 60
    redis_hyde_cache_ttl_seconds: int = 900

    minio_endpoint: str = "127.0.0.1:9000"
    minio_access_key: str = "CHANGE_ME"
    minio_secret_key: str = "CHANGE_ME"
    minio_secure: bool = False
    minio_raw_bucket: str = "kb-raw"
    minio_markdown_bucket: str = "kb-markdown"
    minio_image_bucket: str = "kb-images"
    minio_bucket_name: str = ""
    minio_img_dir: str = ""

    milvus_host: str = "127.0.0.1"
    milvus_port: int = 19530
    milvus_url: str = ""
    milvus_database: str = "default"
    milvus_user: str = "CHANGE_ME"
    milvus_password: str = "CHANGE_ME"
    milvus_collection: str = "kb_chunks"
    chunks_collection: str = ""
    milvus_vector_dim: int = 1024
    milvus_metric_type: str = "COSINE"
    milvus_index_type: str = "HNSW"
    milvus_top_k: int = 20

    mineru_api_token: str = "CHANGE_ME"
    mineru_base_url: str = "https://mineru.net/api/v4"
    mineru_timeout_seconds: int = 600
    mineru_max_file_mb: int = 100
    mineru_concurrency: int = 2
    mineru_poll_interval_seconds: int = 3

    vlm_base_url: str = "http://127.0.0.1:9001/v1"
    vlm_api_key: str = "CHANGE_ME"
    vlm_model: str = "CHANGE_ME"
    vl_model: str = ""
    vlm_timeout_seconds: int = 120
    vlm_max_image_mb: int = 20
    vlm_confidence_threshold: float = 0.75
    vlm_prompt_version: str = "v1"

    openai_api_key: str = "CHANGE_ME"
    openai_base_url: str = "https://api.example.com/v1"
    llm_default_model: str = "qwen-flash"
    llm_timeout_seconds: int = 120
    llm_max_tokens: int = 2048
    llm_default_temperature: float = 0.1
    llm_hyde_count: int = 3
    llm_hyde_max_tokens: int = 512
    llm_hyde_temperature: float = 0.1

    embedding_base_url: str = "https://api.example.com/v1"
    embedding_api_key: str = "CHANGE_ME"
    embedding_model: str = "CHANGE_ME"
    embedding_batch_size: int = 32
    embedding_dimension: int = 1024
    embedding_timeout_seconds: int = 60
    bge_m3: str = ""
    bge_m3_path: str = ""
    bge_device: str = "cpu"
    bge_fp16: bool = False

    reranker_base_url: str = "http://127.0.0.1:9002/v1"
    reranker_api_key: str = "CHANGE_ME"
    reranker_model: str = "CHANGE_ME"
    reranker_top_n: int = 30
    reranker_top_k: int = 8
    reranker_timeout_seconds: int = 60
    text_rerank_base_url: str = ""
    text_rerank_api_key: str = ""
    text_rerank_model: str = ""
    text_rerank_instruct: str = ""

    hybrid_top_k: int = 20
    hyde_top_k: int = 20
    rrf_k: int = 60
    retrieval_default_top_k: int = 8
    faq_sensitive_keywords: str = ""

    # 作用：判断非敏感配置是否已经填写有效值。
    @staticmethod
    def _configured(value: str) -> bool:
        """返回配置值是否非空且不是占位符。"""
        normalized = value.strip()
        return bool(normalized) and not normalized.upper().startswith("CHANGE_ME")

    # 作用：返回原文件、Markdown 和图片使用的有效桶名。
    def effective_minio_bucket(self, purpose: str) -> str:
        """优先使用 env.txt 的统一桶，否则使用业务桶字段。"""
        if self.minio_bucket_name.strip():
            return self.minio_bucket_name.strip()
        buckets = {
            "raw": self.minio_raw_bucket,
            "markdown": self.minio_markdown_bucket,
            "image": self.minio_image_bucket,
        }
        return buckets.get(purpose, self.minio_raw_bucket).strip()

    # 作用：返回图片在统一桶内的对象前缀。
    def effective_image_prefix(self) -> str:
        """返回图片对象键前缀。"""
        return self.minio_img_dir.strip().strip("/")

    # 作用：返回 Milvus 客户端连接地址。
    def effective_milvus_uri(self) -> str:
        """优先使用 MILVUS_URL，兼容旧的 HOST/PORT 配置。"""
        if self.milvus_url.strip():
            return self.milvus_url.strip().rstrip("/")
        return f"http://{self.milvus_host}:{self.milvus_port}"

    # 作用：返回知识切片集合名。
    def effective_milvus_collection(self) -> str:
        """优先使用 CHUNKS_COLLECTION。"""
        return self.chunks_collection.strip() or self.milvus_collection.strip()

    # 作用：返回 VLM 的服务地址、密钥和模型。
    def effective_vlm_config(self) -> tuple[str, str, str]:
        """优先使用 VLM 专用配置，未填写时复用 OpenAI 兼容配置。"""
        base_url = self.vlm_base_url if self._configured(self.vlm_base_url) else self.openai_base_url
        api_key = self.vlm_api_key if self._configured(self.vlm_api_key) else self.openai_api_key
        model = self.vl_model.strip() or self.vlm_model.strip()
        return base_url.strip(), api_key.strip(), model

    # 作用：返回 Reranker 的有效服务配置。
    def effective_reranker_config(self) -> tuple[str, str, str, str]:
        """优先使用 TEXT_RERANK 系列配置。"""
        base_url = self.text_rerank_base_url.strip() or self.reranker_base_url.strip()
        api_key = self.text_rerank_api_key.strip() or self.reranker_api_key.strip()
        model = self.text_rerank_model.strip() or self.reranker_model.strip()
        return base_url, api_key, model, self.text_rerank_instruct.strip()

    # 作用：构造 SQLAlchemy 使用的 MySQL 异步连接字符串。
    def mysql_dsn(self) -> str:
        """返回 MySQL 异步连接地址。"""
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}"
        )

    # 作用：构造 Redis 异步连接字符串。
    def redis_dsn(self) -> str:
        """返回 Redis 连接地址。"""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # 作用：返回 FastAPI/Uvicorn 启动所需的基础参数，不在此处建立任何连接。
    def runtime_options(self) -> dict[str, str | int]:
        """返回应用启动参数。"""
        return {
            "host": self.app_host,
            "port": self.app_port,
            "log_level": self.app_log_level.lower(),
            "workers": self.app_workers,
        }


# 作用：创建供组合根和应用入口使用的默认配置对象。
def get_settings() -> Settings:
    """获取配置对象。"""
    return Settings()
