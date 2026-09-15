"""提供健康检查路由。"""

from fastapi import APIRouter

router = APIRouter(tags=["system"])


# 作用：返回服务运行状态。
@router.get("/health")
async def health() -> dict[str, bool]:
    """健康检查接口。"""
    return {"ok": True}