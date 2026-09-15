"""定义领域和应用层需要的外部能力端口，不包含任何具体实现。"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from kb_manage_platform.domain.models import (
    KnowledgeCategory,
    AccountStatus,
    AnswerResult,
    AuditRecord,
    ConversationMessage,
    ConversationMessageView,
    ConversationSession,
    DashboardOverview,
    Department,
    Faq,
    FaqCandidate,
    FaqCandidateStatus,
    ImageSummary,
    JobRecord,
    KnowledgeChunk,
    KnowledgeGap,
    KnowledgeGapStatus,
    KnowledgeMaintenanceCommand,
    KnowledgePermissionSet,
    KnowledgeStatus,
    KnowledgeUnit,
    KnowledgeVersion,
    ModelConfig,
    PermissionDefinition,
    PermissionGrant,
    QaLogRecord,
    QuestionCluster,
    ResolvedModelConfig,
    RetrievedCandidate,
    SystemSetting,
    Role,
    UserAccount,
    UserContext,
)


class FaqCachePort(Protocol):
    """FAQ 快速应答缓存端口。"""

    # 作用：按问题查找已发布且有权访问的 FAQ 答案。
    async def lookup(self, question: str, user: UserContext) -> AnswerResult | None: ...

    # 作用：写入或刷新 FAQ 缓存。
    async def save(self, question: str, answer: AnswerResult) -> None: ...


class HybridRetrieverPort(Protocol):
    """路线 A：BM25、关键词和 Dense Vector 的混合检索端口。"""

    # 作用：返回原文混合检索候选。
    async def retrieve(
        self, question: str, user: UserContext, top_k: int
    ) -> Sequence[RetrievedCandidate]: ...


class HydeGeneratorPort(Protocol):
    """使用 LangChain 接入 LLM 生成 HyDE 假设文档的端口。"""

    # 作用：根据原问题生成一个或多个假设性答案或假设文档。
    async def generate(self, question: str, count: int) -> Sequence[str]: ...


class VectorRetrieverPort(Protocol):
    """Milvus Dense Vector 检索端口。"""

    # 作用：将输入文本向量化并执行语义检索。
    async def retrieve(self, texts: Sequence[str], user: UserContext, top_k: int) -> Sequence[RetrievedCandidate]: ...


class RerankerPort(Protocol):
    """候选知识精排端口。"""

    # 作用：根据用户问题对 RRF 候选进行重排。
    async def rerank(
        self, question: str, candidates: Sequence[RetrievedCandidate], top_k: int
    ) -> Sequence[RetrievedCandidate]: ...


class AuthorizationPort(Protocol):
    """四维数据权限决策端口。"""

    # 作用：过滤出当前用户有权访问的知识候选。
    async def filter_allowed(
        self, user: UserContext, candidates: Sequence[RetrievedCandidate]
    ) -> Sequence[RetrievedCandidate]: ...


class AnswerGeneratorPort(Protocol):
    """最终回答生成端口。"""

    # 作用：仅使用已授权候选生成回答。
    async def generate(
        self,
        question: str,
        candidates: Sequence[RetrievedCandidate],
        history: Sequence[ConversationMessage] = (),
    ) -> AnswerResult: ...


class AuditPort(Protocol):
    """问答和任务审计端口。"""

    # 作用：记录一次问答或后台任务的审计信息。
    async def record(self, event_type: str, payload: dict[str, object]) -> None: ...


class ModelConfigRepositoryPort(Protocol):
    """模型配置仓储端口。"""

    async def list_all(self) -> Sequence[ModelConfig]: ...

    async def get(self, model_type: str) -> ModelConfig | None: ...

    async def upsert(
        self,
        model_type: str,
        name: str,
        base_url: str,
        model_name: str,
        api_key_ciphertext: str,
        options: dict[str, object],
        status: str,
        operator_id: str,
    ) -> ModelConfig: ...


class ModelRuntimePort(Protocol):
    """将数据库模型配置应用到已装配的运行时客户端。"""

    def apply(self, config: ResolvedModelConfig) -> None: ...


class SystemSettingRepositoryPort(Protocol):
    """系统参数配置仓储端口。"""

    async def list_all(self) -> Sequence[SystemSetting]: ...

    async def upsert(
        self,
        setting_key: str,
        value: object,
        description: str,
        operator_id: str,
    ) -> SystemSetting: ...


class SecretCipherPort(Protocol):
    """密钥加解密端口。"""

    def encrypt(self, plaintext: str) -> str: ...

    def decrypt(self, ciphertext: str) -> str: ...

    @staticmethod
    def mask(plaintext: str) -> str: ...


class AuditQueryPort(Protocol):
    """审计事件查询端口。"""

    async def list_events(
        self,
        event_type: str,
        user_id: str,
        start_at: datetime | None,
        end_at: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[AuditRecord], int]: ...


class ObjectStoragePort(Protocol):
    """MinIO 对象存储端口。"""

    # 作用：保存原始文件、Markdown 或图片并返回对象键。
    async def put_bytes(self, bucket: str, object_key: str, content: bytes, content_type: str) -> str: ...

    # 作用：读取指定桶中的对象内容。
    async def get_bytes(self, bucket: str, object_key: str) -> bytes: ...

    # 作用：删除指定对象。
    async def delete_object(self, bucket: str, object_key: str) -> None: ...

    # 作用：删除指定前缀下的全部对象。
    async def delete_prefix(self, bucket: str, prefix: str) -> int: ...


class DocumentParserPort(Protocol):
    """线上 MinerU 文档解析端口。"""

    # 作用：调用线上 MinerU 将 Word/PDF 对象转换为 Markdown 和图片信息。
    async def parse(self, object_key: str, filename: str) -> tuple[str, Sequence[str]]: ...


class ImageSummarizerPort(Protocol):
    """VLM 图片摘要端口。"""

    # 作用：为图片提取 OCR、描述、实体和摘要。
    async def summarize(self, image_key: str) -> ImageSummary: ...


class ChunkerPort(Protocol):
    """Markdown 切片端口。"""

    # 作用：将 Markdown 和图片摘要切分为知识切片。
    async def chunk(self, markdown: str, images: Sequence[ImageSummary], knowledge_id: str, version_id: str) -> Sequence[KnowledgeChunk]: ...


class EmbedderPort(Protocol):
    """Embedding 模型端口。"""

    # 作用：将知识切片批量转换为向量。
    async def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


class VectorIndexPort(Protocol):
    """Milvus 索引写入端口。"""

    # 作用：写入或更新切片、Dense Vector 与 BM25 索引数据。
    async def upsert(self, chunks: Sequence[KnowledgeChunk], vectors: Sequence[Sequence[float]]) -> None: ...

    # 作用：读取指定知识单元的全部切片。
    async def list_chunks(self, knowledge_id: str) -> Sequence[KnowledgeChunk]: ...

    # 作用：删除指定知识单元的全部向量。
    async def delete_knowledge(self, knowledge_id: str) -> None: ...


class DocumentRepositoryPort(Protocol):
    """知识元数据仓储端口。"""

    # 作用：保存知识单元和版本状态。
    async def save_version(self, request_id: str, knowledge_id: str, version_id: str, state: str) -> None: ...


class JobRepositoryPort(Protocol):
    """MySQL 任务表仓储端口，不依赖 Celery 或 RabbitMQ。"""

    # 作用：创建一个后台任务。
    async def enqueue(self, job_type: str, payload: dict[str, object], idempotency_key: str) -> str: ...

    # 作用：领取一批待执行任务。
    async def claim_batch(self, worker_id: str, batch_size: int) -> Sequence[JobRecord]: ...

    # 作用：标记任务执行成功。
    async def mark_succeeded(self, job_id: str) -> None: ...

    # 作用：标记任务失败并按策略设置重试时间。
    async def mark_failed(self, job_id: str, error: str, retry: bool) -> None: ...

    # 作用：回收心跳超时的任务。
    async def release_stale(self, timeout_seconds: int) -> int: ...

    # 作用：按 ID 查询任务状态。
    async def get(self, job_id: str) -> JobRecord | None: ...

    # 作用：更新任务阶段和进度。
    async def update_progress(self, job_id: str, stage: str, progress: int) -> None: ...

    # 作用：将失败任务重新放入待处理队列。
    async def retry(self, job_id: str) -> None: ...

class KnowledgeRepositoryPort(Protocol):
    """知识单元与版本仓储端口。"""

    # 作用：创建一个新的知识单元草稿。
    async def create_unit(self, command: KnowledgeMaintenanceCommand) -> KnowledgeUnit: ...

    # 作用：按知识 ID 查询知识单元。
    async def get_unit(self, knowledge_id: str) -> KnowledgeUnit | None: ...

    # 作用：更新知识单元标题、分类和标签。
    async def update_metadata(self, knowledge_id: str, title: str, category_id: str, tags: tuple[str, ...], operator_id: str) -> KnowledgeUnit: ...

    # 作用：保存一个新的版本文档。
    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion: ...

    # 作用：查询知识单元当前版本文档。
    async def get_current_version(self, knowledge_id: str) -> KnowledgeVersion | None: ...

    # 作用：分页查询知识单元。
    async def list_units(
        self,
        query: str,
        status: KnowledgeStatus | None,
        category_id: str,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[KnowledgeUnit], int]: ...

    # 作用：查询知识单元的全部版本。
    async def list_versions(self, knowledge_id: str) -> Sequence[KnowledgeVersion]: ...

    # 作用：按版本 ID 查询版本文档。
    async def get_version(self, knowledge_id: str, version_id: str) -> KnowledgeVersion | None: ...

    # 作用：将已索引的历史版本切换为当前版本。
    async def activate_version(self, knowledge_id: str, version_id: str, operator_id: str) -> KnowledgeVersion: ...

    # 作用：物理删除知识单元及其版本。
    async def delete_unit(self, knowledge_id: str) -> None: ...

    # 作用：更新知识单元生命周期状态。
    async def set_unit_status(self, knowledge_id: str, status: KnowledgeStatus, operator_id: str) -> KnowledgeUnit: ...


class KnowledgeCategoryRepositoryPort(Protocol):
    """知识分类字典仓储端口。"""

    async def list_all(self) -> Sequence[KnowledgeCategory]: ...

    async def create(
        self, category_id: str, name: str, description: str, sort_order: int
    ) -> KnowledgeCategory: ...

    async def update(
        self,
        category_id: str,
        name: str,
        description: str,
        status: str,
        sort_order: int,
    ) -> KnowledgeCategory: ...

    async def delete(self, category_id: str) -> None: ...


class KnowledgePermissionRepositoryPort(Protocol):
    """知识单元四维权限仓储端口。"""

    # 作用：整体替换一个知识单元的权限规则。
    async def replace_grants(self, knowledge_id: str, grants: tuple[PermissionGrant, ...], operator_id: str) -> KnowledgePermissionSet: ...

    # 作用：查询一个知识单元当前权限规则。
    async def list_grants(self, knowledge_id: str) -> KnowledgePermissionSet: ...

    # 作用：批量查询多个知识单元的权限规则。
    async def list_grants_batch(
        self, knowledge_ids: Sequence[str]
    ) -> dict[str, KnowledgePermissionSet]: ...


class PermissionVersionPort(Protocol):
    """权限版本和缓存失效端口。"""

    # 作用：递增知识或用户权限版本并使相关缓存失效。
    async def invalidate(self, knowledge_id: str, affected_user_ids: tuple[str, ...] = ()) -> int: ...

class IdentityRepositoryPort(Protocol):
    """用户身份、部门和角色查询端口。"""

    # 作用：按用户 ID 加载可信用户上下文。
    async def get_user_context(self, user_id: str) -> UserContext: ...


class ConversationRepositoryPort(Protocol):
    """问答会话和消息仓储端口。"""

    # 作用：读取指定用户会话的最近消息。
    async def get_recent_messages(self, session_id: str, user_id: str, limit: int) -> tuple[ConversationMessage, ...]: ...

    # 作用：保存一轮用户问题和助手回答。
    async def save_turn(
        self,
        request_id: str,
        session_id: str,
        user_id: str,
        question: str,
        answer: AnswerResult,
    ) -> None: ...

    # 作用：查询指定用户的会话列表。
    async def list_sessions(self, user_id: str) -> Sequence[ConversationSession]: ...

    # 作用：查询指定会话的完整消息和引用。
    async def list_messages(self, session_id: str, user_id: str) -> Sequence[ConversationMessageView]: ...

    # 作用：重命名当前用户的会话。
    async def rename_session(self, session_id: str, user_id: str, title: str) -> ConversationSession: ...

    # 作用：删除当前用户的会话及消息引用。
    async def delete_session(self, session_id: str, user_id: str) -> None: ...


class DashboardRepositoryPort(Protocol):
    """运营看板聚合查询端口。"""

    # 作用：返回指定时间范围的看板指标。
    async def overview(
        self,
        range_days: int,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        department_id: str = "",
    ) -> DashboardOverview: ...


class QaLogRepositoryPort(Protocol):
    """问答审计日志读取端口。"""

    # 作用：读取指定时间窗口内的有效问答记录。
    async def list_logs(self, window_days: int, limit: int = 5000) -> Sequence[QaLogRecord]: ...


class QuestionClustererPort(Protocol):
    """问答文本语义聚类端口。"""

    # 作用：按语义相似度阈值聚合历史问题。
    async def cluster(
        self,
        logs: Sequence[QaLogRecord],
        threshold: float,
    ) -> Sequence[QuestionCluster]: ...


class FaqManagementRepositoryPort(Protocol):
    """FAQ 候选和发布管理端口。"""

    # 作用：批量保存 FAQ 候选。
    async def save_candidates(self, candidates: Sequence[FaqCandidate]) -> None: ...

    # 作用：按 ID 查询 FAQ 候选。
    async def get_candidate(self, candidate_id: str) -> FaqCandidate | None: ...

    # 作用：按状态查询 FAQ 候选。
    async def list_candidates(self, status: FaqCandidateStatus | None = None) -> Sequence[FaqCandidate]: ...

    # 作用：发布候选 FAQ 并写入独立权限。
    async def publish_candidate(self, candidate_id: str, grants: tuple[PermissionGrant, ...], operator_id: str) -> str: ...

    # 作用：驳回候选 FAQ。
    async def reject_candidate(self, candidate_id: str, operator_id: str, reason: str) -> None: ...

    # 作用：查询已发布 FAQ。
    async def list_published(self) -> Sequence[Faq]: ...

    # 作用：更新已发布 FAQ 的标准问题和答案。
    async def update_published(self, faq_id: str, question: str, answer: str, operator_id: str) -> Faq: ...

    # 作用：启用或停用已发布 FAQ。
    async def set_published_status(self, faq_id: str, status: str, operator_id: str) -> Faq: ...


class KnowledgeGapRepositoryPort(Protocol):
    """知识缺口和补充草稿端口。"""

    # 作用：批量保存或聚合知识缺口。
    async def upsert_gaps(self, gaps: Sequence[KnowledgeGap]) -> None: ...

    # 作用：按 ID 查询知识缺口。
    async def get_gap(self, gap_id: str) -> KnowledgeGap | None: ...

    # 作用：按状态查询知识缺口。
    async def list_gaps(self, status: KnowledgeGapStatus | None = None) -> Sequence[KnowledgeGap]: ...

    # 作用：创建缺口与知识补充草稿的关联。
    async def create_supplement_draft(self, gap_id: str, title: str, category_id: str, knowledge_id: str, operator_id: str) -> str: ...

    # 作用：根据知识单元发布结果自动解决关联缺口。
    async def resolve_by_knowledge(self, knowledge_id: str) -> int: ...

    # 作用：更新知识缺口状态。
    async def set_status(self, gap_id: str, status: KnowledgeGapStatus, reason: str = "") -> None: ...


class FaqCacheInvalidationPort(Protocol):
    """FAQ 缓存失效端口。"""

    # 作用：按标准问题清理全部用户维度的 FAQ 缓存。
    async def invalidate_question(self, question: str) -> None: ...


class PasswordHasherPort(Protocol):
    """密码哈希端口。"""

    # 作用：计算密码哈希。
    def hash(self, password: str) -> str: ...

    # 作用：校验明文密码与哈希。
    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenPort(Protocol):
    """访问令牌签发和解析端口。"""

    # 作用：签发访问令牌。
    def issue(self, user_id: str, permission_version: int) -> tuple[str, int]: ...

    # 作用：解析访问令牌。
    def parse(self, token: str) -> tuple[str, int]: ...


class DepartmentRepositoryPort(Protocol):
    """部门仓储端口。"""

    # 作用：创建部门。
    async def create(
        self, name: str, parent_id: str, operator_id: str, sort_order: int = 0
    ) -> Department: ...

    # 作用：更新部门名称或父部门。
    async def update(
        self,
        department_id: str,
        name: str,
        parent_id: str,
        operator_id: str,
        sort_order: int = 0,
    ) -> Department: ...

    # 作用：按 ID 查询部门。
    async def get(self, department_id: str) -> Department | None: ...

    # 作用：查询全部部门。
    async def list_all(self) -> Sequence[Department]: ...

    # 作用：更新部门状态。
    async def set_status(self, department_id: str, status: str) -> Department: ...

    # 作用：删除部门。
    async def delete(self, department_id: str) -> None: ...


class AccountRepositoryPort(Protocol):
    """用户账号仓储端口。"""

    # 作用：创建本地账号。
    async def create(self, username: str, password_hash: str, department_id: str, role_ids: tuple[str, ...]) -> UserAccount: ...

    # 作用：按用户名查询账号及密码哈希。
    async def get_by_username(self, username: str) -> tuple[UserAccount, str] | None: ...

    # 作用：按用户 ID 查询账号。
    async def get(self, user_id: str) -> UserAccount | None: ...

    # 作用：查询账号列表。
    async def list_all(self) -> Sequence[UserAccount]: ...

    # 作用：更新账号状态。
    async def set_status(self, user_id: str, status: AccountStatus) -> UserAccount: ...

    # 作用：替换用户角色。
    async def assign_roles(self, user_id: str, role_ids: tuple[str, ...]) -> UserAccount: ...

    # 作用：重置用户密码。
    async def update_password_hash(self, user_id: str, password_hash: str) -> None: ...

    # 作用：记录登录失败次数和锁定时间。
    async def record_login_failure(self, user_id: str, failed_attempts: int, locked_until) -> None: ...

    # 作用：清除登录失败记录。
    async def clear_login_failures(self, user_id: str) -> None: ...

    # 作用：递增用户权限版本，使已有令牌失效。
    async def bump_permission_version(self, user_id: str) -> int: ...


class RoleRepositoryPort(Protocol):
    """角色与操作权限仓储端口。"""

    # 作用：创建角色。
    async def create(self, name: str, permission_codes: tuple[str, ...]) -> Role: ...

    # 作用：按 ID 查询角色。
    async def get(self, role_id: str) -> Role | None: ...

    # 作用：查询角色列表。
    async def list_all(self) -> Sequence[Role]: ...

    # 作用：更新角色状态。
    async def set_status(self, role_id: str, status: str) -> Role: ...

    # 作用：替换角色操作权限。
    async def set_permissions(self, role_id: str, permission_codes: tuple[str, ...]) -> Role: ...

    # 作用：删除未被用户引用的角色。
    async def delete(self, role_id: str) -> None: ...

    # 作用：查询系统支持的操作权限定义。
    async def list_permissions(self) -> Sequence[PermissionDefinition]: ...




