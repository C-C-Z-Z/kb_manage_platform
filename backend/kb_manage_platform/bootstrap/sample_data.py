"""写入可直接在控制台查看的演示数据。"""

import asyncio
import hashlib
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert

from kb_manage_platform.bootstrap.settings import get_settings
from kb_manage_platform.infrastructure.adapters.chunk_utils import BasicChunker
from kb_manage_platform.infrastructure.adapters.embedding_utils import ModelEmbedder
from kb_manage_platform.infrastructure.adapters.milvus_utils import MilvusStore, MilvusVectorIndex
from kb_manage_platform.infrastructure.adapters.storage_utils import MinioObjectStorage
from kb_manage_platform.infrastructure.mysql.models import (
    DepartmentModel,
    FaqCandidateModel,
    FaqModel,
    FaqPermissionModel,
    KnowledgeGapModel,
    KnowledgeGapSourceModel,
    KnowledgePermissionModel,
    KnowledgeUnitModel,
    KnowledgeVersionModel,
    QaAuditModel,
    QaCitationModel,
    QaMessageModel,
    QaSessionModel,
)
from kb_manage_platform.infrastructure.mysql.session import Database


def normalized_hash(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().casefold())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def main() -> None:
    settings = get_settings()
    database = Database(settings.mysql_dsn(), pool_size=3)
    storage = MinioObjectStorage(
        settings.minio_endpoint,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.minio_secure,
    )
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
    vector_index = MilvusVectorIndex(milvus_store)
    samples = []
    try:
        async with database.session_factory() as session:
            await _seed_departments(session)
            samples = await _seed_knowledge(
                session,
                storage,
                settings.effective_minio_bucket("raw"),
                settings.effective_minio_bucket("markdown"),
            )
            await _seed_faqs(session)
            await _seed_faq_candidates(session)
            await _seed_gaps(session)
            await _seed_conversations(session)
            await _seed_audits(session)
            await session.commit()
        await _seed_vectors(samples, embedder, vector_index)
    finally:
        await database.dispose()


async def _seed_vectors(samples, embedder: ModelEmbedder, vector_index: MilvusVectorIndex) -> None:
    chunker = BasicChunker()
    for item in samples:
        if item["status"] != "published":
            continue
        chunks = await chunker.chunk(item["content"], (), item["knowledge_id"], item["version_id"])
        vectors = await embedder.embed([chunk.content for chunk in chunks])
        await vector_index.upsert(chunks, vectors)


async def _seed_departments(session) -> None:
    rows = [
        {"department_id": "dept-finance", "name": "财务部", "parent_id": "dept-root", "path": "dept-root/dept-finance", "status": "active", "sort_order": 20},
        {"department_id": "dept-operation", "name": "运营中心", "parent_id": "dept-root", "path": "dept-root/dept-operation", "status": "active", "sort_order": 30},
    ]
    for row in rows:
        await session.execute(insert(DepartmentModel).prefix_with("IGNORE").values(**row))
    await session.execute(
        DepartmentModel.__table__.update()
        .where(DepartmentModel.department_id == "dept-root")
        .values(name="总公司")
    )


async def _seed_knowledge(session, storage, raw_bucket: str, markdown_bucket: str):
    samples = [
        {
            "knowledge_id": "sample-kb-travel",
            "version_id": "version-sample-kb-travel",
            "title": "差旅报销管理制度",
            "category_id": "finance",
            "tags": ["差旅", "报销", "财务"],
            "status": "published",
            "filename": "差旅报销管理制度.md",
            "content": """# 差旅报销管理制度

## 适用范围
本制度适用于因公出差、参加培训和客户拜访产生的交通、住宿和补贴费用。

## 报销材料
1. 出差申请审批记录。
2. 合法有效的发票或电子票据。
3. 行程单、住宿清单等辅助凭证。
4. 超过 5000 元时需附部门负责人审批意见。

## 提交时限
出差结束后 15 个工作日内提交报销申请。
""",
        },
        {
            "knowledge_id": "sample-kb-annual-leave",
            "version_id": "version-sample-kb-annual-leave",
            "title": "年假申请与审批流程",
            "category_id": "hr",
            "tags": ["年假", "考勤", "员工制度"],
            "status": "published",
            "filename": "年假申请与审批流程.md",
            "content": """# 年假申请与审批流程

1. 员工在办公系统提交年假申请。
2. 直属主管审批工作安排和交接事项。
3. 连续休假超过 3 天时，需部门负责人复核。
4. 审批通过后，系统自动更新考勤记录。

年假原则上应提前 3 个工作日申请，紧急情况可补交说明。
""",
        },
        {
            "knowledge_id": "sample-kb-release",
            "version_id": "version-sample-kb-release",
            "title": "产品版本发布规范",
            "category_id": "product",
            "tags": ["版本发布", "研发流程", "质量"],
            "status": "published",
            "filename": "产品版本发布规范.md",
            "content": """# 产品版本发布规范

## 发布前检查
- 完成需求验收和回归测试。
- 数据库变更脚本通过评审。
- 回滚方案和值班人员已确认。

## 发布窗口
生产发布默认安排在工作日 20:00 至 22:00。重大版本需提前两个工作日通知相关团队。
""",
        },
        {
            "knowledge_id": "sample-kb-security",
            "version_id": "version-sample-kb-security",
            "title": "信息安全事件上报流程",
            "category_id": "general",
            "tags": ["信息安全", "应急", "流程"],
            "status": "draft",
            "filename": "信息安全事件上报流程.md",
            "content": """# 信息安全事件上报流程

发现账号泄露、恶意邮件、数据异常访问等情况时，应立即停止高风险操作并联系信息安全值班人员。

上报内容应包括发生时间、影响范围、已采取措施和联系人。
""",
        },
    ]
    for item in samples:
        object_prefix = f"samples/knowledge/{item['knowledge_id']}/{item['version_id']}"
        raw_key = f"{object_prefix}/{item['filename']}"
        markdown_key = f"{object_prefix}/document.md"
        content = item["content"].encode("utf-8")
        await storage.put_bytes(raw_bucket, raw_key, content, "text/markdown; charset=utf-8")
        await storage.put_bytes(markdown_bucket, markdown_key, content, "text/markdown; charset=utf-8")
        await session.execute(
            insert(KnowledgeUnitModel).prefix_with("IGNORE").values(
                knowledge_id=item["knowledge_id"],
                title=item["title"],
                category_id=item["category_id"],
                tags=item["tags"],
                status=item["status"],
                current_version_id=item["version_id"],
                created_by="user-admin",
                updated_by="user-admin",
            )
        )
        await session.execute(
            insert(KnowledgeVersionModel).prefix_with("IGNORE").values(
                version_id=item["version_id"],
                knowledge_id=item["knowledge_id"],
                version_no=1,
                source_object_key=raw_key,
                markdown_object_key=markdown_key,
                filename=item["filename"],
                content_type="text/markdown; charset=utf-8",
                status="indexed" if item["status"] == "published" else "processing",
                error_message="",
                created_by="user-admin",
            )
        )
        await session.execute(
            insert(KnowledgePermissionModel).prefix_with("IGNORE").values(
                knowledge_id=item["knowledge_id"],
                scope="global",
                subject_id="",
                include_descendants=False,
                permission_version=1,
                created_by="user-admin",
                updated_by="user-admin",
            )
        )
    return samples


async def _seed_faqs(session) -> None:
    rows = [
        ("faq-sample-annual-leave", "年假如何申请？", "在办公系统提交年假申请，经直属主管审批；连续休假超过 3 天时还需部门负责人复核。"),
        ("faq-sample-invoice", "发票抬头填错怎么办？", "请联系开票方作废或红冲原发票，并使用正确的公司抬头和税号重新开具。"),
    ]
    for faq_id, question, answer in rows:
        await session.execute(
            insert(FaqModel).prefix_with("IGNORE").values(
                faq_id=faq_id,
                standard_question=question,
                normalized_hash=normalized_hash(question),
                answer_text=answer,
                status="published",
            )
        )
        await session.execute(
            insert(FaqPermissionModel).prefix_with("IGNORE").values(
                faq_id=faq_id,
                scope="global",
                subject_id="",
                include_descendants=False,
            )
        )


async def _seed_faq_candidates(session) -> None:
    rows = [
        ("candidate-sample-reimburse-time", "报销多久到账？", "审批完成后通常 5 至 10 个工作日到账。", 18, 11, 0.93),
        ("candidate-sample-device", "办公电脑如何申请？", "在 IT 服务台提交设备申请，直属主管审批后由 IT 部门统一采购或调配。", 9, 6, 0.86),
    ]
    for candidate_id, question, answer, frequency, users, confidence in rows:
        await session.execute(
            insert(FaqCandidateModel).prefix_with("IGNORE").values(
                candidate_id=candidate_id,
                representative_question=question,
                normalized_hash=normalized_hash(question),
                standard_answer=answer,
                frequency=frequency,
                distinct_users=users,
                permission_signature="global",
                status="pending_review",
                confidence=confidence,
            )
        )


async def _seed_gaps(session) -> None:
    rows = [
        ("gap-sample-meal-subsidy", "加班餐补标准是多少？", "no_candidate", "pending", 14, ["dept-product"], 0.28, "general"),
        ("gap-sample-partner-access", "外部合作方如何申请系统访问权限？", "low_confidence", "pending", 7, ["dept-operation"], 0.72, "general"),
    ]
    for gap_id, question, gap_type, status, frequency, departments, similarity, category in rows:
        await session.execute(
            insert(KnowledgeGapModel).prefix_with("IGNORE").values(
                gap_id=gap_id,
                representative_question=question,
                normalized_hash=normalized_hash(question),
                gap_type=gap_type,
                status=status,
                frequency=frequency,
                department_ids=departments,
                max_similarity=similarity,
                suggested_category=category,
                reason="",
            )
        )
        await session.execute(
            insert(KnowledgeGapSourceModel).prefix_with("IGNORE").values(
                gap_id=gap_id,
                request_id=f"source-{gap_id}",
            )
        )


async def _seed_conversations(session) -> None:
    sessions = [
        ("sample-session-travel", "user-admin", "差旅报销制度咨询"),
        ("sample-session-leave", "user-demo", "年假申请咨询"),
    ]
    for session_id, user_id, title in sessions:
        await session.execute(
            insert(QaSessionModel).prefix_with("IGNORE").values(
                session_id=session_id,
                user_id=user_id,
                title=title,
            )
        )
    messages = [
        ("sample-msg-1", "sample-session-travel", "user-admin", "demo-req-1", "user", "差旅报销需要哪些材料？"),
        ("sample-msg-2", "sample-session-travel", "user-admin", "demo-req-1", "assistant", "需要出差审批记录、合法发票或电子票据、行程单或住宿清单；超过 5000 元还需部门负责人审批，并在出差结束后 15 个工作日内提交。"),
        ("sample-msg-3", "sample-session-leave", "user-demo", "demo-req-2", "user", "年假怎么申请？"),
        ("sample-msg-4", "sample-session-leave", "user-demo", "demo-req-2", "assistant", "请在办公系统提交年假申请，由直属主管审批；连续休假超过 3 天时还需部门负责人复核。"),
    ]
    for message_id, session_id, user_id, request_id, role, content in messages:
        await session.execute(
            insert(QaMessageModel).prefix_with("IGNORE").values(
                message_id=message_id,
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                role=role,
                content=content,
            )
        )
    citation_exists = await session.scalar(
        select(QaCitationModel.id).where(
            QaCitationModel.message_id == "sample-msg-2",
            QaCitationModel.chunk_id == "sample-chunk-travel-1",
        ).limit(1)
    )
    if not citation_exists:
        session.add(
            QaCitationModel(
                message_id="sample-msg-2",
                knowledge_id="sample-kb-travel",
                version_id="version-sample-kb-travel",
                chunk_id="sample-chunk-travel-1",
                title="差旅报销管理制度",
                section_path="报销材料",
                snippet="出差申请审批记录、合法有效的发票或电子票据、行程单和住宿清单。",
            )
        )


async def _seed_audits(session) -> None:
    questions = [
        "差旅报销需要哪些材料？",
        "年假如何申请？",
        "产品版本发布需要哪些检查？",
        "发票抬头错了怎么办？",
        "加班餐补标准是多少？",
        "外部合作方如何申请系统权限？",
    ]
    now = datetime.now(UTC)
    for index, question in enumerate(questions):
        request_id = f"sample-audit-{index + 1}"
        exists = await session.scalar(select(QaAuditModel.id).where(QaAuditModel.request_id == request_id).limit(1))
        if exists:
            continue
        created_at = now - timedelta(days=index % 7, hours=index)
        faq_hit = index in {1, 3}
        authorized_count = 0 if index == 4 else 3
        payload = {
            "request_id": request_id,
            "session_id": f"sample-session-{index + 1}",
            "user_id": "user-admin" if index % 2 == 0 else "user-demo",
            "question": question,
            "faq_hit": faq_hit,
            "recall_count": 8 + index,
            "authorized_count": authorized_count,
            "blocked_count": 1 if index == 4 else 0,
            "final_count": 3 if authorized_count else 0,
            "answer_excerpt": "示例回答：请以公司正式制度为准。",
        }
        audit = QaAuditModel(event_type="qa.completed", request_id=request_id, user_id=payload["user_id"], payload=payload)
        audit.created_at = created_at
        session.add(audit)
        metrics = QaAuditModel(
            event_type="qa.metrics",
            request_id=request_id,
            user_id=payload["user_id"],
            payload={
                "request_id": request_id,
                "user_id": payload["user_id"],
                "latency_ms": 620.0 + index * 85,
                "estimated_tokens": 180 + index * 35,
                "demo": True,
            },
        )
        metrics.created_at = created_at
        session.add(metrics)


if __name__ == "__main__":
    asyncio.run(main())
