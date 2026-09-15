"""文档导入 API 的请求和响应模型。"""

from pydantic import BaseModel, Field


class ImportRequest(BaseModel):
    """提交已上传对象的导入请求。"""

    knowledge_id: str = Field(..., min_length=1)
    version_id: str = Field(..., min_length=1)
    original_object_key: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    content_type: str = Field(default="application/octet-stream")


class ImportResponse(BaseModel):
    """文档导入响应。"""

    job_id: str
    status: str
    progress: int = 0
    stage: str = "queued"


class ImportJobResponse(BaseModel):
    """导入任务状态响应。"""

    job_id: str
    job_type: str
    status: str
    progress: int
    stage: str
    attempts: int
    max_attempts: int
    last_error: str = ""
    created_at: str = ""
    updated_at: str = ""
