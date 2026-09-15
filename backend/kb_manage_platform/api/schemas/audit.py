"""审计日志 API 模型。"""

from pydantic import BaseModel

from kb_manage_platform.domain.models import AuditRecord


class AuditLogResponse(BaseModel):
    event_id: int
    event_type: str
    request_id: str
    user_id: str
    payload: dict[str, object]
    created_at: str = ""

    @classmethod
    def from_domain(cls, item: AuditRecord) -> "AuditLogResponse":
        return cls(
            event_id=item.event_id,
            event_type=item.event_type,
            request_id=item.request_id,
            user_id=item.user_id,
            payload=item.payload,
            created_at=item.created_at.isoformat() if item.created_at else "",
        )


class AuditLogPageResponse(BaseModel):
    items: list[AuditLogResponse]
    page: int
    page_size: int
    total: int