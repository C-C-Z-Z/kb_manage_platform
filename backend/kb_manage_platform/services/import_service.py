"""提供文档上传和入库任务应用服务。"""

from pathlib import PurePosixPath
from uuid import uuid4

from kb_manage_platform.domain.models import IngestionRequest, JobRecord
from kb_manage_platform.domain.ports import JobRepositoryPort, ObjectStoragePort
from kb_manage_platform.engines.ingestion_engine.main_graph import KBImportWorkflow


class ImportService:
    """编排文档上传、任务提交和 LangGraph 入库执行。"""

    _SUPPORTED_SUFFIXES = {".pdf", ".doc", ".docx", ".md", ".markdown", ".txt"}

    # 作用：注入任务仓储、对象存储和入库引擎。
    def __init__(
        self,
        job_repository: JobRepositoryPort,
        object_storage: ObjectStoragePort,
        raw_bucket: str,
        workflow: KBImportWorkflow,
    ) -> None:
        self._job_repository = job_repository
        self._object_storage = object_storage
        self._raw_bucket = raw_bucket
        self._workflow = workflow

    # 作用：保存上传文件并提交文档入库任务。
    async def upload_and_submit(
        self,
        request_id: str,
        user_id: str,
        knowledge_id: str,
        version_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> str:
        """写入 MinIO、创建 MySQL 任务并返回任务 ID。"""
        safe_name = PurePosixPath(filename).name
        suffix = PurePosixPath(safe_name).suffix.lower()
        if suffix not in self._SUPPORTED_SUFFIXES:
            raise ValueError(f"unsupported file type: {suffix}")
        object_key = f"knowledge/{knowledge_id}/{version_id}/{uuid4().hex}-{safe_name}"
        await self._object_storage.put_bytes(
            self._raw_bucket,
            object_key,
            content,
            content_type or "application/octet-stream",
        )
        return await self.submit(
            request_id=request_id,
            user_id=user_id,
            knowledge_id=knowledge_id,
            version_id=version_id,
            original_object_key=object_key,
            filename=safe_name,
            content_type=content_type or "application/octet-stream",
        )

    # 作用：提交已上传到 MinIO 的文档入库任务。
    async def submit(
        self,
        request_id: str,
        user_id: str,
        knowledge_id: str,
        version_id: str,
        original_object_key: str,
        filename: str,
        content_type: str,
    ) -> str:
        """写入 MySQL 任务并返回任务 ID。"""
        return await self._job_repository.enqueue(
            "ingest_document",
            {
                "request_id": request_id,
                "user_id": user_id,
                "knowledge_id": knowledge_id,
                "version_id": version_id,
                "original_object_key": original_object_key,
                "filename": filename,
                "content_type": content_type,
            },
            idempotency_key=f"{knowledge_id}:{version_id}",
        )

    # 作用：按 ID 查询导入任务状态。
    async def get_job(self, job_id: str) -> JobRecord | None:
        """返回任务记录。"""
        return await self._job_repository.get(job_id)

    # 作用：重试失败的导入任务。
    async def retry_job(self, job_id: str) -> None:
        """将失败任务重新入队。"""
        job = await self.get_job(job_id)
        if job is None or job.job_type != "ingest_document":
            raise LookupError("import job not found")
        await self._job_repository.retry(job_id)  # type: ignore

    # 作用：执行 MySQL 中领取到的入库任务。
    async def execute(self, job: JobRecord) -> None:
        """调用知识入库 LangGraph并更新阶段进度。"""
        payload = job.payload
        await self._job_repository.update_progress(job.job_id, "parsing", 10)
        await self._workflow.ainvoke(
            {
                "request": IngestionRequest(
                    request_id=str(payload["request_id"]),
                    user_id=str(payload["user_id"]),
                    knowledge_id=str(payload["knowledge_id"]),
                    version_id=str(payload["version_id"]),
                    original_object_key=str(payload["original_object_key"]),
                    filename=str(payload["filename"]),
                    content_type=str(payload["content_type"]),
                )
            }
        )
        await self._job_repository.update_progress(job.job_id, "indexing", 90)


