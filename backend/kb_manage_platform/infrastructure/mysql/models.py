"""定义知识维护和四维权限所需的 MySQL ORM 模型。"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from kb_manage_platform.infrastructure.mysql.base import Base


class KnowledgeCategoryModel(Base):
    """知识分类字典表。"""

    __tablename__ = "knowledge_category"

    category_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KnowledgeUnitModel(Base):
    """知识单元表。"""

    __tablename__ = "knowledge_unit"

    knowledge_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    current_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KnowledgeVersionModel(Base):
    """知识版本文档表。"""

    __tablename__ = "knowledge_version"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    knowledge_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(nullable=False)
    source_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    markdown_object_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgePermissionModel(Base):
    """知识单元四维数据权限表。"""

    __tablename__ = "knowledge_permission"
    __table_args__ = (
        UniqueConstraint("knowledge_id", "scope", "subject_id", "include_descendants", name="uq_knowledge_permission"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    include_descendants: Mapped[bool] = mapped_column(nullable=False, default=False)
    permission_version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class BackgroundJobModel(Base):
    """MySQL 后台任务表。"""

    __tablename__ = "background_job"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(nullable=False, default=0)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(nullable=False, default=3)
    progress: Mapped[int] = mapped_column(nullable=False, default=0)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DepartmentModel(Base):
    """组织部门表。"""

    __tablename__ = "iam_department"

    department_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    path: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)


class UserModel(Base):
    """用户身份表。"""

    __tablename__ = "iam_user"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    department_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    permission_version: Mapped[int] = mapped_column(nullable=False, default=1)
    failed_login_attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RoleModel(Base):
    """角色表。"""

    __tablename__ = "iam_role"

    role_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class UserRoleModel(Base):
    """用户角色关联表。"""

    __tablename__ = "iam_user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class FaqModel(Base):
    """已发布 FAQ 事实表。"""

    __tablename__ = "knowledge_faq"

    faq_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    standard_question: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    knowledge_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    version_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FaqPermissionModel(Base):
    """FAQ 四维权限表。"""

    __tablename__ = "knowledge_faq_permission"
    __table_args__ = (UniqueConstraint("faq_id", "scope", "subject_id", "include_descendants", name="uq_faq_permission"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    faq_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    include_descendants: Mapped[bool] = mapped_column(nullable=False, default=False)


class QaSessionModel(Base):
    """问答会话表。"""

    __tablename__ = "qa_session"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class QaMessageModel(Base):
    """问答消息表。"""

    __tablename__ = "qa_message"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QaCitationModel(Base):
    """回答引用知识快照表。"""

    __tablename__ = "qa_citation"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    knowledge_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    section_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ModelConfigModel(Base):
    """模型服务配置表。"""

    __tablename__ = "model_config"

    config_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_ciphertext: Mapped[str] = mapped_column(Text, nullable=False, default="")
    options: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SystemSettingModel(Base):
    """系统参数配置表。"""

    __tablename__ = "system_setting"

    setting_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class QaAuditModel(Base):
    """问答审计日志表。"""

    __tablename__ = "qa_audit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FaqCandidateModel(Base):
    """FAQ 聚类候选表。"""

    __tablename__ = "knowledge_faq_candidate"

    candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    representative_question: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    standard_answer: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[int] = mapped_column(nullable=False, default=0)
    distinct_users: Mapped[int] = mapped_column(nullable=False, default=0)
    permission_signature: Mapped[str] = mapped_column(String(128), nullable=False, default="mixed")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    reviewed_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    reject_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FaqCandidateSourceModel(Base):
    """FAQ 候选来源审计关联表。"""

    __tablename__ = "knowledge_faq_candidate_source"
    __table_args__ = (UniqueConstraint("candidate_id", "request_id", name="uq_faq_candidate_source"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class KnowledgeGapModel(Base):
    """知识缺口聚合表。"""

    __tablename__ = "knowledge_gap"

    gap_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    representative_question: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    gap_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    frequency: Mapped[int] = mapped_column(nullable=False, default=0)
    department_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    max_similarity: Mapped[float] = mapped_column(nullable=False, default=0.0)
    suggested_category: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KnowledgeGapSourceModel(Base):
    """知识缺口来源问答关联表。"""

    __tablename__ = "knowledge_gap_source"
    __table_args__ = (UniqueConstraint("gap_id", "request_id", name="uq_gap_source"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gap_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class KnowledgeSupplementDraftModel(Base):
    """知识补充草稿与缺口关联表。"""

    __tablename__ = "knowledge_supplement_draft"

    draft_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    gap_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str] = mapped_column(String(64), nullable=False)
    knowledge_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IamPermissionModel(Base):
    """菜单、按钮和接口操作权限。"""

    __tablename__ = "iam_permission"

    permission_code: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    permission_type: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_code: Mapped[str] = mapped_column(String(128), nullable=False, default="")


class RolePermissionModel(Base):
    """角色操作权限关联表。"""

    __tablename__ = "iam_role_permission"
    __table_args__ = (UniqueConstraint("role_id", "permission_code", name="uq_role_permission"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    permission_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

