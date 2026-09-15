"""定义不依赖 Web、数据库、Milvus 或模型 SDK 的领域模型。"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


@dataclass(frozen=True, slots=True)
class UserContext:
    """一次请求中的用户身份与数据权限上下文。"""

    user_id: str
    department_id: str
    role_ids: tuple[str, ...]
    permission_version: int
    is_active: bool = True
    department_path: tuple[str, ...] = ()
    permission_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RetrievedCandidate:
    """检索得到的候选知识切片。"""

    chunk_id: str
    knowledge_id: str
    version_id: str
    content: str
    score: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    """完成切片后、尚未向量化的知识内容。"""

    chunk_id: str
    knowledge_id: str
    version_id: str
    content: str
    section_path: str = ""
    image_summary: str = ""


@dataclass(frozen=True, slots=True)
class ImageSummary:
    """VLM 对单张图片的提取结果。"""

    image_key: str
    summary: str
    confidence: float
    model_name: str
    prompt_version: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievalPolicy:
    """问答检索和重排参数。"""

    hybrid_top_k: int = 20
    hyde_top_k: int = 20
    rrf_top_k: int = 30
    reranker_top_k: int = 8

@dataclass(frozen=True, slots=True)
class ConversationMessage:
    """一轮会话消息。"""

    role: str
    content: str
    request_id: str = ""

@dataclass(frozen=True, slots=True)
class QuestionRequest:
    """问答请求的最小领域输入。"""

    request_id: str
    user: UserContext
    question: str
    session_id: str = ""
    history: tuple[ConversationMessage, ...] = ()


@dataclass(frozen=True, slots=True)
class AnswerResult:
    """问答生成结果。"""

    answer: str
    citations: tuple[RetrievedCandidate, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IngestionRequest:
    """文档入库请求的最小领域输入。"""

    request_id: str
    user_id: str
    original_object_key: str
    filename: str
    content_type: str
    knowledge_id: str
    version_id: str


class JobStatus(StrEnum):
    """MySQL 任务表的任务状态。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStage(StrEnum):
    """文档入库任务的业务阶段。"""

    QUEUED = "queued"
    PARSING = "parsing"
    SUMMARIZING = "summarizing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JobRecord:
    """后台 Worker 使用的最小任务记录。"""

    job_id: str
    job_type: str
    payload: dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    idempotency_key: str = ""
    progress: int = 0
    stage: JobStage = JobStage.QUEUED
    last_error: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

class KnowledgeStatus(StrEnum):
    """知识单元生命周期状态。"""

    DRAFT = "draft"
    PUBLISHED = "published"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class VersionStatus(StrEnum):
    """版本文档处理状态。"""

    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class PermissionScope(StrEnum):
    """四维数据权限类型。"""

    GLOBAL = "global"
    DEPARTMENT = "department"
    ROLE = "role"
    USER = "user"


class KnowledgeAction(StrEnum):
    """知识维护工作流动作。"""

    CREATE = "create"
    UPDATE_METADATA = "update_metadata"
    CREATE_VERSION = "create_version"
    CONFIGURE_PERMISSIONS = "configure_permissions"
    PUBLISH = "publish"
    DISABLE = "disable"
    ARCHIVE = "archive"
@dataclass(frozen=True, slots=True)
class KnowledgeCategory:
    """知识分类字典项。"""

    category_id: str
    name: str
    description: str = ""
    status: str = "active"
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeUnit:
    """知识单元聚合根。"""

    knowledge_id: str
    title: str
    category_id: str
    tags: tuple[str, ...]
    status: KnowledgeStatus
    created_by: str
    updated_by: str
    current_version_id: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeVersion:
    """知识版本文档。"""

    version_id: str
    knowledge_id: str
    version_no: int
    source_object_key: str
    filename: str
    content_type: str
    status: VersionStatus
    created_by: str
    markdown_object_key: str = ""
    error_message: str = ""
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PermissionGrant:
    """单条四维数据权限规则。"""

    scope: PermissionScope
    subject_id: str
    include_descendants: bool = False


@dataclass(frozen=True, slots=True)
class KnowledgePermissionSet:
    """一个知识单元的四维权限集合。"""

    knowledge_id: str
    grants: tuple[PermissionGrant, ...]
    permission_version: int = 0


@dataclass(frozen=True, slots=True)
class KnowledgeMaintenanceCommand:
    """知识维护和权限配置工作流命令。"""

    action: KnowledgeAction
    request_id: str
    operator_id: str
    knowledge_id: str = ""
    title: str = ""
    category_id: str = ""
    tags: tuple[str, ...] = ()
    source_object_key: str = ""
    filename: str = ""
    content_type: str = ""
    grants: tuple[PermissionGrant, ...] = ()


@dataclass(frozen=True, slots=True)
class KnowledgeMaintenanceResult:
    """知识维护流程执行结果。"""

    knowledge_id: str
    status: KnowledgeStatus
    version_id: str = ""
    job_id: str = ""
    permission_version: int = 0


@dataclass(frozen=True, slots=True)
class Faq:
    """已发布 FAQ 管理读模型。"""

    faq_id: str
    standard_question: str
    answer_text: str
    status: str
    knowledge_id: str = ""
    version_id: str = ""
    updated_at: datetime | None = None


class FaqCandidateStatus(StrEnum):
    """FAQ 候选状态。"""

    CANDIDATE = "candidate"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    REJECTED = "rejected"


class FaqReviewDecision(StrEnum):
    """FAQ 人工审核结果。"""

    APPROVE = "approve"
    REJECT = "reject"


class KnowledgeGapType(StrEnum):
    """知识缺口类型。"""

    NO_CANDIDATE = "no_candidate"
    LOW_CONFIDENCE = "low_confidence"


class KnowledgeGapStatus(StrEnum):
    """知识缺口处理状态。"""

    PENDING = "pending"
    CONVERTED = "converted"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class FaqGapAction(StrEnum):
    """FAQ 与知识缺口工作流动作。"""

    MINE_FAQ = "mine_faq"
    REVIEW_FAQ = "review_faq"
    DETECT_GAPS = "detect_gaps"
    CONVERT_GAP = "convert_gap"
    RESOLVE_GAP = "resolve_gap"


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """模型服务配置。"""

    config_id: str
    model_type: str
    name: str
    base_url: str
    model_name: str
    api_key_ciphertext: str
    options: dict[str, Any]
    status: str = "active"
    updated_by: str = ""
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ResolvedModelConfig:
    """可立即应用到运行时客户端的明文模型配置。"""

    model_type: str
    base_url: str
    model_name: str
    api_key: str
    options: dict[str, Any]
    status: str = "active"


@dataclass(frozen=True, slots=True)
class SystemSetting:
    """系统参数配置。"""

    setting_key: str
    value: Any
    description: str = ""
    updated_by: str = ""
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """审计事件读模型。"""

    event_id: int
    event_type: str
    request_id: str
    user_id: str
    payload: dict[str, Any]
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class QaLogRecord:
    """用于 FAQ 挖掘和缺口识别的问答审计记录。"""

    request_id: str
    user_id: str
    department_id: str
    question: str
    recall_count: int
    authorized_count: int
    final_count: int
    answer_excerpt: str
    permission_signatures: tuple[str, ...]
    authorized_knowledge_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FaqCandidate:
    """FAQ 聚类候选。"""

    candidate_id: str
    representative_question: str
    standard_answer: str
    frequency: int
    distinct_users: int
    permission_signature: str
    status: FaqCandidateStatus
    confidence: float
    source_request_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class KnowledgeGap:
    """知识缺口聚合记录。"""

    gap_id: str
    representative_question: str
    gap_type: KnowledgeGapType
    status: KnowledgeGapStatus
    frequency: int
    department_ids: tuple[str, ...]
    max_similarity: float
    suggested_category: str
    source_request_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class KnowledgeSupplementDraft:
    """知识补充草稿关联记录。"""

    draft_id: str
    gap_id: str
    title: str
    category_id: str
    knowledge_id: str
    status: str
    created_by: str


@dataclass(frozen=True, slots=True)
class FaqGapCommand:
    """FAQ 与知识缺口工作流命令。"""

    action: FaqGapAction
    request_id: str
    operator_id: str
    window_days: int = 30
    similarity_threshold: float = 0.85
    min_occurrences: int = 10
    min_users: int = 5
    candidate_id: str = ""
    gap_id: str = ""
    question: str = ""
    decision: str = ""
    standard_answer: str = ""
    title: str = ""
    category_id: str = ""
    reason: str = ""
    grants: tuple[PermissionGrant, ...] = ()


@dataclass(frozen=True, slots=True)
class FaqGapResult:
    """FAQ 与知识缺口工作流结果。"""

    action: FaqGapAction
    processed_count: int
    candidate_ids: tuple[str, ...] = ()
    gap_ids: tuple[str, ...] = ()
    draft_id: str = ""


@dataclass(frozen=True, slots=True)
class QuestionCluster:
    """相似问题聚类结果。"""

    representative_question: str
    logs: tuple[QaLogRecord, ...]
    similarity: float


class AccountStatus(StrEnum):
    """账号状态。"""

    ACTIVE = "active"
    DISABLED = "disabled"
    LOCKED = "locked"


@dataclass(frozen=True, slots=True)
class Department:
    """组织部门。"""

    department_id: str
    name: str
    parent_id: str = ""
    path: str = ""
    status: str = "active"
    sort_order: int = 0


@dataclass(frozen=True, slots=True)
class UserAccount:
    """账号管理视图。"""

    user_id: str
    username: str
    department_id: str
    status: AccountStatus
    permission_version: int
    role_ids: tuple[str, ...] = ()
    failed_login_attempts: int = 0
    locked_until_epoch: int = 0


@dataclass(frozen=True, slots=True)
class Role:
    """角色定义。"""

    role_id: str
    name: str
    status: str = "active"
    permission_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AuthToken:
    """登录令牌结果。"""

    access_token: str
    token_type: str
    expires_in: int
    user_context: UserContext


@dataclass(frozen=True, slots=True)
class DashboardTopItem:
    """看板排行榜条目。"""

    label: str
    value: float


@dataclass(frozen=True, slots=True)
class DashboardTrendPoint:
    """看板时间趋势点。"""

    label: str
    value: float


@dataclass(frozen=True, slots=True)
class DashboardOverview:
    """运营看板聚合结果。"""

    range_days: int
    pv: int
    uv: int
    knowledge_count: int
    published_count: int
    top_questions: tuple[DashboardTopItem, ...]
    hot_knowledge: tuple[DashboardTopItem, ...]
    token_total: int
    avg_latency_ms: float
    faq_hit_rate: float
    coverage_rate: float
    token_trend: tuple[DashboardTrendPoint, ...]
    latency_trend: tuple[DashboardTrendPoint, ...]


@dataclass(frozen=True, slots=True)
class ConversationSession:
    """会话列表读模型。"""

    session_id: str
    title: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ConversationMessageView:
    """会话消息读模型。"""

    message_id: str
    role: str
    content: str
    request_id: str
    created_at: datetime | None = None
    citations: tuple[RetrievedCandidate, ...] = ()


@dataclass(frozen=True, slots=True)
class PermissionDefinition:
    """操作权限定义。"""

    permission_code: str
    name: str
    permission_type: str
    parent_code: str = ""






