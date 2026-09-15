"""文档上传与导入任务路由。"""

from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile

from kb_manage_platform.api.dependencies import (
    ImportCreateUserDep,
    ImportReadUserDep,
    ImportServiceDep,
)
from kb_manage_platform.api.schemas.import_ import ImportJobResponse, ImportRequest, ImportResponse
from kb_manage_platform.common.errors import NotFoundError

router = APIRouter(prefix="/import", tags=["import"])


@router.post("", response_model=ImportResponse)
async def import_document(
    payload: ImportRequest,
    user: ImportCreateUserDep,
    service: ImportServiceDep,
) -> ImportResponse:
    """创建已上传对象的解析与索引任务。"""
    job_id = await service.submit(
        request_id=str(uuid4()),
        user_id=user.user_id,
        knowledge_id=payload.knowledge_id,
        version_id=payload.version_id,
        original_object_key=payload.original_object_key,
        filename=payload.filename,
        content_type=payload.content_type,
    )
    return ImportResponse(job_id=job_id, status="pending")


@router.post("/files", response_model=ImportResponse)
async def upload_document(
    user: ImportCreateUserDep,
    service: ImportServiceDep,
    knowledge_id: str = Form(...),
    version_id: str = Form(...),
    filename: str = Form(...),
    content_type: str = Form(default="application/octet-stream"),
    file: UploadFile = File(...),
) -> ImportResponse:
    """上传原始文档并提交入库任务。"""
    job_id = await service.upload_and_submit(
        request_id=str(uuid4()),
        user_id=user.user_id,
        knowledge_id=knowledge_id,
        version_id=version_id,
        filename=filename,
        content_type=content_type,
        content=await file.read(),
    )
    return ImportResponse(job_id=job_id, status="pending")


@router.get("/jobs/{job_id}", response_model=ImportJobResponse)
async def get_import_job(
    job_id: str,
    _: ImportReadUserDep,
    service: ImportServiceDep,
) -> ImportJobResponse:
    """查询导入任务进度。"""
    job = await service.get_job(job_id)
    if job is None or job.job_type != "ingest_document":
        raise NotFoundError("import job not found")
    return ImportJobResponse(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status.value,
        progress=job.progress,
        stage=job.stage.value,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        last_error=job.last_error,
        created_at=job.created_at.isoformat() if job.created_at else "",
        updated_at=job.updated_at.isoformat() if job.updated_at else "",
    )


@router.post("/jobs/{job_id}/retry", response_model=ImportResponse)
async def retry_import_job(
    job_id: str,
    _: ImportCreateUserDep,
    service: ImportServiceDep,
) -> ImportResponse:
    """重试失败的导入任务。"""
    await service.retry_job(job_id)
    return ImportResponse(job_id=job_id, status="pending")
