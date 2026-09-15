"""创建并配置 FastAPI 应用。"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from kb_manage_platform.api.router import api_router
from kb_manage_platform.bootstrap.container import build_container
from kb_manage_platform.bootstrap.settings import get_settings
from kb_manage_platform.common.errors import (
    AppError,
    AuthorizationError,
    ConflictError,
    DependencyUnavailableError,
    NotFoundError,
    ValidationError,
)


class ApplicationFactory:
    """应用工厂，负责装配 FastAPI 与依赖容器。"""

    @staticmethod
    def create() -> FastAPI:
        """返回应用实例。"""
        settings = get_settings()

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncIterator[None]:
            """初始化并释放组合根。"""
            container = build_container(settings)
            await container.configuration_service.initialize_runtime()
            app.state.container = container
            try:
                yield
            finally:
                await container.close()

        app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
        origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.include_router(api_router, prefix=settings.app_api_prefix)

        @app.middleware("http")
        async def request_id_middleware(request: Request, call_next):
            """为每个请求补充可审计的 request ID。"""
            request_id = request.headers.get("X-Request-ID", "") or str(uuid4())
            request.state.request_id = request_id
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        async def error_response(request: Request, error: AppError) -> JSONResponse:
            """将业务异常转换为稳定错误响应。"""
            request_id = getattr(request.state, "request_id", request.headers.get("X-Request-ID", ""))
            return JSONResponse(
                status_code=error.status_code,
                content={
                    "code": error.code,
                    "message": error.message,
                    "details": error.details,
                    "request_id": request_id,
                },
            )

        @app.exception_handler(AppError)
        async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
            """处理业务异常。"""
            return await error_response(request, exc)

        @app.exception_handler(RequestValidationError)
        async def validation_error_handler(
            request: Request, exc: RequestValidationError
        ) -> JSONResponse:
            """统一 FastAPI 参数校验错误。"""
            error = ValidationError("request validation failed", {"errors": exc.errors()})
            return await error_response(request, error)

        @app.exception_handler(PermissionError)
        async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
            """统一资源归属校验错误。"""
            return await error_response(request, AuthorizationError(str(exc)))

        @app.exception_handler(LookupError)
        async def lookup_error_handler(request: Request, exc: LookupError) -> JSONResponse:
            """统一资源不存在错误。"""
            return await error_response(request, NotFoundError(str(exc)))

        @app.exception_handler(ValueError)
        async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
            """统一业务参数错误。"""
            return await error_response(request, ValidationError(str(exc)))

        @app.exception_handler(IntegrityError)
        async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
            """处理数据库约束冲突。"""
            return await error_response(request, ConflictError("database constraint conflict"))

        @app.exception_handler(SQLAlchemyError)
        async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
            """处理数据库不可用。"""
            return await error_response(request, DependencyUnavailableError("database temporarily unavailable"))

        static_dir = Path(__file__).resolve().parents[2] / "static"
        if static_dir.exists():
            assets_dir = static_dir / "assets"
            if assets_dir.exists():
                app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

            @app.get("/{full_path:path}", include_in_schema=False)
            async def spa_fallback(full_path: str):
                """将前端静态文件和 Vue Router 路由交给浏览器。"""
                if full_path.startswith("api/"):
                    raise NotFoundError("api route not found")
                candidate = (static_dir / full_path).resolve()
                if candidate.is_file() and static_dir.resolve() in candidate.parents:
                    return FileResponse(candidate)
                return FileResponse(static_dir / "index.html")

        return app


app = ApplicationFactory.create()
