"""审计日志查询与导出路由。"""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Response

from kb_manage_platform.api.dependencies import AuditExportUserDep, AuditReadUserDep, AuditServiceDep
from kb_manage_platform.api.schemas.audit import AuditLogPageResponse, AuditLogResponse
from kb_manage_platform.common.errors import ValidationError

router = APIRouter(prefix="/audit", tags=["audit"])


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"invalid datetime: {value}") from exc


@router.get("/logs", response_model=AuditLogPageResponse)
async def list_audit_logs(
    _: AuditReadUserDep,
    service: AuditServiceDep,
    event_type: str = "",
    user_id: str = "",
    start_at: str = "",
    end_at: str = "",
    page: int = 1,
    page_size: int = 20,
) -> AuditLogPageResponse:
    """分页查询审计日志。"""
    normalized_page = max(1, page)
    normalized_size = max(1, min(page_size, 100))
    rows, total = await service.list_events(
        event_type,
        user_id,
        _parse_datetime(start_at),
        _parse_datetime(end_at),
        normalized_page,
        normalized_size,
    )
    return AuditLogPageResponse(
        items=[AuditLogResponse.from_domain(item) for item in rows],
        page=normalized_page,
        page_size=normalized_size,
        total=total,
    )


@router.get("/export")
async def export_audit_logs(
    _: AuditExportUserDep,
    service: AuditServiceDep,
    event_type: str = "",
    user_id: str = "",
    start_at: str = "",
    end_at: str = "",
) -> Response:
    """导出审计日志 CSV。"""
    rows = await service.export_events(
        event_type, user_id, _parse_datetime(start_at), _parse_datetime(end_at)
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["event_id", "event_type", "request_id", "user_id", "created_at", "payload"])
    for item in rows:
        writer.writerow(
            [
                item.event_id,
                item.event_type,
                item.request_id,
                item.user_id,
                item.created_at.isoformat() if item.created_at else "",
                str(item.payload),
            ]
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="audit-logs.csv"'},
    )