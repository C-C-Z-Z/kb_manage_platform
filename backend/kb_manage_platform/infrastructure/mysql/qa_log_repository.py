"""使用 SQLAlchemy 读取 FAQ 挖掘和缺口分析所需的问答日志。"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kb_manage_platform.domain.models import PermissionGrant, PermissionScope, QaLogRecord
from kb_manage_platform.domain.services.permissions import permission_signature
from kb_manage_platform.infrastructure.mysql.models import KnowledgePermissionModel, QaAuditModel


class MysqlQaLogRepository:
    """问答审计日志读取仓储。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # 作用：读取指定时间窗口内的有效问答记录。
    async def list_logs(self, window_days: int, limit: int = 5000) -> tuple[QaLogRecord, ...]:
        """返回带当前知识权限签名的问答审计记录。"""
        cutoff = datetime.now(UTC) - timedelta(days=window_days)
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(QaAuditModel)
                    .where(
                        QaAuditModel.event_type == "qa.completed",
                        QaAuditModel.created_at >= cutoff,
                    )
                    .order_by(QaAuditModel.created_at.asc())
                    .limit(limit)
                )
            ).all()
            payloads = [dict(row.payload) for row in rows]
            knowledge_ids = tuple(
                {
                    knowledge_id
                    for payload in payloads
                    for knowledge_id in self._authorized_knowledge_ids(payload)
                }
            )
            signatures_by_knowledge: dict[str, str] = {}
            if knowledge_ids:
                permission_rows = (
                    await session.scalars(
                        select(KnowledgePermissionModel).where(
                            KnowledgePermissionModel.knowledge_id.in_(knowledge_ids)
                        )
                    )
                ).all()
                grants_by_knowledge: dict[str, list[PermissionGrant]] = defaultdict(list)
                for permission in permission_rows:
                    grants_by_knowledge[permission.knowledge_id].append(
                        PermissionGrant(
                            scope=PermissionScope(permission.scope),
                            subject_id=permission.subject_id,
                            include_descendants=permission.include_descendants,
                        )
                    )
                signatures_by_knowledge = {
                    knowledge_id: permission_signature(
                        grants_by_knowledge.get(knowledge_id, [])
                    )
                    for knowledge_id in knowledge_ids
                }
        return tuple(
            self._to_record(payload, signatures_by_knowledge)
            for payload in payloads
        )

    # 作用：从审计载荷读取已授权知识 ID。
    @staticmethod
    def _authorized_knowledge_ids(payload: dict[str, object]) -> tuple[str, ...]:
        raw_ids = payload.get("authorized_knowledge_ids", [])
        if not isinstance(raw_ids, (list, tuple, set)):
            return ()
        return tuple(str(item) for item in raw_ids if str(item).strip())

    # 作用：将审计 JSON 转换为领域记录。
    @classmethod
    def _to_record(
        cls,
        payload: dict[str, object],
        signatures_by_knowledge: dict[str, str] | None = None,
    ) -> QaLogRecord:
        """转换审计记录，并优先按当前知识权限重算签名。"""
        authorized_knowledge_ids = cls._authorized_knowledge_ids(payload)
        payload_signatures = tuple(
            str(item)
            for item in payload.get("permission_signatures", [])
            if str(item).strip()
        ) if isinstance(payload.get("permission_signatures", []), (list, tuple, set)) else ()
        computed_signatures: tuple[str, ...] = ()
        if signatures_by_knowledge:
            computed_signatures = tuple(
                sorted(
                    {
                        signatures_by_knowledge.get(knowledge_id, "restricted")
                        for knowledge_id in authorized_knowledge_ids
                    }
                )
            )
        signatures = computed_signatures or payload_signatures
        if not signatures and int(payload.get("authorized_count", 0) or 0) > 0:
            signatures = ("unknown",)
        return QaLogRecord(
            request_id=str(payload.get("request_id", "")),
            user_id=str(payload.get("user_id", "")),
            department_id=str(payload.get("department_id", "")),
            question=str(payload.get("question", "")),
            recall_count=int(payload.get("recall_count", 0)),
            authorized_count=int(payload.get("authorized_count", 0)),
            final_count=int(payload.get("final_count", 0)),
            answer_excerpt=str(payload.get("answer_excerpt", "")),
            permission_signatures=signatures,
            authorized_knowledge_ids=authorized_knowledge_ids,
        )