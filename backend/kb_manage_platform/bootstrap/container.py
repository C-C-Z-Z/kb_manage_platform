"""集中装配配置、适配器、LangGraph 工作流和后台任务组件。"""

from redis.asyncio import Redis

from kb_manage_platform.bootstrap.settings import Settings
from kb_manage_platform.domain.models import RetrievalPolicy
from kb_manage_platform.domain.services.faq_gap import SensitiveContentChecker
from kb_manage_platform.domain.services.permissions import PermissionPolicy
from kb_manage_platform.domain.services.rrf import RrfFuser
from kb_manage_platform.engines.faq_gap_engine.main_graph import FaqGapWorkflow
from kb_manage_platform.engines.ingestion_engine.main_graph import KBImportWorkflow
from kb_manage_platform.engines.knowledge_engine.main_graph import KnowledgeMaintenanceWorkflow
from kb_manage_platform.engines.query_engine.main_graph import KBQueryWorkflow
from kb_manage_platform.infrastructure.adapters.cache_utils import RedisFaqCache
from kb_manage_platform.infrastructure.adapters.chunk_utils import BasicChunker
from kb_manage_platform.infrastructure.adapters.embedding_utils import ModelEmbedder
from kb_manage_platform.infrastructure.adapters.faq_cluster_utils import EmbeddingQuestionClusterer
from kb_manage_platform.infrastructure.adapters.llm_utils import (
    LangChainAnswerGenerator,
    LangChainHydeGenerator,
)
from kb_manage_platform.infrastructure.adapters.milvus_utils import MilvusStore, MilvusVectorIndex
from kb_manage_platform.infrastructure.adapters.mineru_utils import MineruDocumentParser
from kb_manage_platform.infrastructure.adapters.model_runtime import ModelRuntimeConfigurator
from kb_manage_platform.infrastructure.adapters.permission_version_utils import RedisPermissionVersionStore
from kb_manage_platform.infrastructure.adapters.reranker_utils import ModelReranker
from kb_manage_platform.infrastructure.adapters.retrieval_utils import (
    MilvusHybridRetriever,
    MilvusVectorRetriever,
)
from kb_manage_platform.infrastructure.adapters.secret_utils import LocalSecretCipher
from kb_manage_platform.infrastructure.adapters.security_utils import JwtTokenService, ScryptPasswordHasher
from kb_manage_platform.infrastructure.adapters.storage_utils import MinioObjectStorage
from kb_manage_platform.infrastructure.adapters.vlm_utils import VlmImageSummarizer
from kb_manage_platform.infrastructure.mysql.account_repository import MysqlAccountRepository
from kb_manage_platform.infrastructure.mysql.category_repository import MysqlKnowledgeCategoryRepository
from kb_manage_platform.infrastructure.mysql.config_repository import (
    MysqlModelConfigRepository,
    MysqlSystemSettingRepository,
)
from kb_manage_platform.infrastructure.adapters.audit_utils import SqlAlchemyAuditLogger
from kb_manage_platform.infrastructure.adapters.auth_utils import SqlAlchemyAuthorizer
from kb_manage_platform.infrastructure.mysql.dashboard_repository import MysqlDashboardRepository
from kb_manage_platform.infrastructure.mysql.conversation_repository import MysqlConversationRepository
from kb_manage_platform.infrastructure.mysql.department_repository import MysqlDepartmentRepository
from kb_manage_platform.infrastructure.mysql.faq_repository import MysqlFaqRepository
from kb_manage_platform.infrastructure.mysql.gap_repository import MysqlKnowledgeGapRepository
from kb_manage_platform.infrastructure.mysql.identity_repository import MysqlIdentityRepository
from kb_manage_platform.infrastructure.mysql.job_repository import MysqlJobRepository
from kb_manage_platform.infrastructure.mysql.knowledge_repository import MysqlKnowledgeRepository
from kb_manage_platform.infrastructure.mysql.permission_repository import MysqlKnowledgePermissionRepository
from kb_manage_platform.infrastructure.mysql.qa_log_repository import MysqlQaLogRepository
from kb_manage_platform.infrastructure.mysql.role_repository import MysqlRoleRepository
from kb_manage_platform.infrastructure.mysql.session import Database
from kb_manage_platform.services.account_service import AccountService
from kb_manage_platform.services.audit_service import AuditService
from kb_manage_platform.services.auth_service import AuthService
from kb_manage_platform.services.category_service import CategoryService
from kb_manage_platform.services.configuration_service import ConfigurationService
from kb_manage_platform.services.dashboard_service import DashboardService
from kb_manage_platform.services.faq_gap_service import FaqGapService
from kb_manage_platform.services.import_service import ImportService
from kb_manage_platform.services.knowledge_service import KnowledgeService
from kb_manage_platform.services.organization_service import OrganizationService
from kb_manage_platform.services.query_service import QueryService
from kb_manage_platform.services.role_service import RoleService


class Container:
    """应用组合根，只负责创建对象和传递依赖。"""

    # 作用：保存配置、工作流、数据库和 Redis 连接。
    def __init__(
        self,
        settings: Settings,
        database: Database,
        redis_client: Redis,
        query_workflow: KBQueryWorkflow,
        import_workflow: KBImportWorkflow,
        knowledge_workflow: KnowledgeMaintenanceWorkflow,
        knowledge_service: KnowledgeService,
        query_service: QueryService,
        import_service: ImportService,
        faq_gap_service: FaqGapService,
        auth_service: AuthService,
        organization_service: OrganizationService,
        account_service: AccountService,
        role_service: RoleService,
        dashboard_service: DashboardService,
        audit_service: AuditService,
        configuration_service: ConfigurationService,
        category_service: CategoryService,
        job_repository: MysqlJobRepository,
    ) -> None:
        self.settings = settings
        self.database = database
        self.redis_client = redis_client
        self.query_workflow = query_workflow
        self.import_workflow = import_workflow
        self.knowledge_workflow = knowledge_workflow
        self.knowledge_service = knowledge_service
        self.query_service = query_service
        self.import_service = import_service
        self.faq_gap_service = faq_gap_service
        self.auth_service = auth_service
        self.organization_service = organization_service
        self.account_service = account_service
        self.role_service = role_service
        self.dashboard_service = dashboard_service
        self.audit_service = audit_service
        self.configuration_service = configuration_service
        self.category_service = category_service
        self.job_repository = job_repository

    # 作用：释放数据库和 Redis 连接。
    async def close(self) -> None:
        """关闭基础设施连接。"""
        await self.database.dispose()
        await self.redis_client.aclose()


# 作用：构建应用依赖图，具体实现均在基础设施适配器中替换。
def build_container(settings: Settings) -> Container:
    """创建应用容器。"""
    database = Database(settings.mysql_dsn(), pool_size=settings.mysql_pool_size)
    redis_client: Redis = Redis.from_url(settings.redis_dsn(), decode_responses=True)
    audit = SqlAlchemyAuditLogger(database.session_factory)
    audit_service = AuditService(audit)
    model_config_repository = MysqlModelConfigRepository(database.session_factory)
    system_setting_repository = MysqlSystemSettingRepository(database.session_factory)
    secret_cipher = LocalSecretCipher(settings.jwt_secret_key)

    permission_policy = PermissionPolicy()
    authorizer = SqlAlchemyAuthorizer(database.session_factory, permission_policy)
    faq_repository = MysqlFaqRepository(database.session_factory, permission_policy)
    identity_repository = MysqlIdentityRepository(database.session_factory)
    department_repository = MysqlDepartmentRepository(database.session_factory)
    account_repository = MysqlAccountRepository(database.session_factory)
    role_repository = MysqlRoleRepository(database.session_factory)
    conversation_repository = MysqlConversationRepository(database.session_factory)
    qa_log_repository = MysqlQaLogRepository(database.session_factory)
    dashboard_repository = MysqlDashboardRepository(database.session_factory)
    gap_repository = MysqlKnowledgeGapRepository(database.session_factory)
    knowledge_repository = MysqlKnowledgeRepository(database.session_factory)
    category_repository = MysqlKnowledgeCategoryRepository(database.session_factory)
    permission_repository = MysqlKnowledgePermissionRepository(database.session_factory)
    job_repository = MysqlJobRepository(database.session_factory)

    password_hasher = ScryptPasswordHasher()
    token_service = JwtTokenService(
        settings.jwt_secret_key,
        settings.jwt_expires_seconds,
        settings.jwt_issuer,
    )
    auth_service = AuthService(
        account_repository,
        identity_repository,
        password_hasher,
        token_service,
        audit,
        settings.password_lock_threshold,
        settings.password_lock_seconds,
    )
    organization_service = OrganizationService(department_repository, audit)
    account_service = AccountService(account_repository, password_hasher, audit)
    role_service = RoleService(role_repository, audit)

    storage = MinioObjectStorage(
        settings.minio_endpoint,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.minio_secure,
    )
    raw_bucket = settings.effective_minio_bucket("raw")
    markdown_bucket = settings.effective_minio_bucket("markdown")
    image_bucket = settings.effective_minio_bucket("image")
    embedder = ModelEmbedder(
        settings.embedding_base_url,
        settings.embedding_api_key,
        settings.embedding_model,
        settings.embedding_batch_size,
        settings.embedding_timeout_seconds,
        settings.bge_m3,
        settings.bge_m3_path,
        settings.bge_device,
        settings.bge_fp16,
    )
    milvus_store = MilvusStore(
        uri=settings.effective_milvus_uri(),
        collection_name=settings.effective_milvus_collection(),
        vector_dim=settings.embedding_dimension or settings.milvus_vector_dim,
        metric_type=settings.milvus_metric_type,
        index_type=settings.milvus_index_type,
        user="" if settings.milvus_user.upper().startswith("CHANGE_ME") else settings.milvus_user,
        password="" if settings.milvus_password.upper().startswith("CHANGE_ME") else settings.milvus_password,
        database=settings.milvus_database,
    )
    hyde_generator = LangChainHydeGenerator(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.llm_default_model,
        temperature=settings.llm_hyde_temperature,
        max_tokens=settings.llm_hyde_max_tokens,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    answer_generator = LangChainAnswerGenerator(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.llm_default_model,
        temperature=settings.llm_default_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    reranker_url, reranker_key, reranker_model, reranker_instruct = settings.effective_reranker_config()
    reranker = ModelReranker(
        reranker_url,
        reranker_key,
        reranker_model,
        reranker_instruct,
        settings.reranker_timeout_seconds,
    )
    vlm_url, vlm_key, vlm_model = settings.effective_vlm_config()
    image_summarizer = VlmImageSummarizer(
        storage=storage,
        image_bucket=image_bucket,
        base_url=vlm_url,
        api_key=vlm_key,
        model=vlm_model,
        timeout_seconds=settings.vlm_timeout_seconds,
        max_image_mb=settings.vlm_max_image_mb,
        confidence_threshold=settings.vlm_confidence_threshold,
        prompt_version=settings.vlm_prompt_version,
    )
    model_runtime = ModelRuntimeConfigurator(
        hyde_generator=hyde_generator,
        answer_generator=answer_generator,
        embedder=embedder,
        reranker=reranker,
        image_summarizer=image_summarizer,
    )
    configuration_service = ConfigurationService(
        settings,
        model_config_repository,
        system_setting_repository,
        secret_cipher,
        audit,
        model_runtime,
    )

    policy = RetrievalPolicy(
        hybrid_top_k=settings.hybrid_top_k,
        hyde_top_k=settings.hyde_top_k,
        rrf_top_k=max(settings.reranker_top_n, settings.retrieval_default_top_k),
        reranker_top_k=settings.reranker_top_k,
    )
    rrf_fuser = RrfFuser(rank_constant=settings.rrf_k)
    faq_cache = RedisFaqCache(redis_client, faq_repository, settings.redis_cache_ttl_seconds)
    query_workflow = KBQueryWorkflow(
        faq_cache=faq_cache,
        hybrid_retriever=MilvusHybridRetriever(milvus_store, embedder),
        hyde_generator=hyde_generator,
        vector_retriever=MilvusVectorRetriever(milvus_store, embedder),
        reranker=reranker,
        authorizer=authorizer,
        answer_generator=answer_generator,
        audit=audit,
        policy=policy,
        hyde_count=settings.llm_hyde_count,
        rrf_fuser=rrf_fuser,
    )
    vector_index = MilvusVectorIndex(milvus_store)
    import_workflow = KBImportWorkflow(
        parser=MineruDocumentParser(
            storage=storage,
            api_token=settings.mineru_api_token,
            base_url=settings.mineru_base_url,
            raw_bucket=raw_bucket,
            markdown_bucket=markdown_bucket,
            image_bucket=image_bucket,
            image_prefix=settings.effective_image_prefix(),
            timeout_seconds=settings.mineru_timeout_seconds,
            poll_interval_seconds=settings.mineru_poll_interval_seconds,
            max_file_mb=settings.mineru_max_file_mb,
        ),
        image_summarizer=image_summarizer,
        chunker=BasicChunker(),
        embedder=embedder,
        vector_index=vector_index,
        repository=knowledge_repository,
        audit=audit,
    )
    faq_gap_workflow = FaqGapWorkflow(
        qa_log_repository=qa_log_repository,
        faq_repository=faq_repository,  # type: ignore[arg-type]
        gap_repository=gap_repository,  # type: ignore[arg-type]
        knowledge_repository=knowledge_repository,
        cache=faq_cache,
        audit=audit,
        sensitive_checker=SensitiveContentChecker(
            tuple(keyword.strip() for keyword in settings.faq_sensitive_keywords.split(",") if keyword.strip())
        ),
        question_clusterer=EmbeddingQuestionClusterer(embedder),
    )
    knowledge_workflow = KnowledgeMaintenanceWorkflow(
        repository=knowledge_repository,
        permission_repository=permission_repository,
        permission_version=RedisPermissionVersionStore(redis_client),
        job_repository=job_repository,
        audit=audit,
        permission_policy=permission_policy,
    )
    return Container(
        settings=settings,
        database=database,
        redis_client=redis_client,
        query_workflow=query_workflow,
        import_workflow=import_workflow,
        knowledge_workflow=knowledge_workflow,
        knowledge_service=KnowledgeService(
            knowledge_workflow,
            gap_repository,
            knowledge_repository,
            permission_repository,
            storage,
            raw_bucket,
            permission_policy,
            markdown_bucket,
            image_bucket,
            vector_index,
        ),
        query_service=QueryService(query_workflow, identity_repository, conversation_repository, audit),
        import_service=ImportService(job_repository, storage, raw_bucket, import_workflow),
        faq_gap_service=FaqGapService(faq_gap_workflow, faq_repository, gap_repository, faq_cache),  # type: ignore[arg-type]
        auth_service=auth_service,
        organization_service=organization_service,
        account_service=account_service,
        role_service=role_service,
        dashboard_service=DashboardService(dashboard_repository),
        audit_service=audit_service,
        configuration_service=configuration_service,
        category_service=CategoryService(category_repository, audit),
        job_repository=job_repository,
    )


