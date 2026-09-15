"""兼容 Uvicorn 的应用入口。"""

from kb_manage_platform.api.app import app

__all__ = ["app"]

# 作用：支持通过 python -m kb_manage_platform.main 启动服务。
if __name__ == "__main__":
    import uvicorn

    from kb_manage_platform.bootstrap.settings import get_settings

    runtime = get_settings().runtime_options()
    uvicorn.run(
        "kb_manage_platform.main:app",
        host=str(runtime["host"]),
        port=int(runtime["port"]),
        log_level=str(runtime["log_level"]),
        reload=True,
    )