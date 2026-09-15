"""定义应用统一业务异常。"""


class AppError(Exception):
    """所有可映射业务异常的基类。"""

    code = "APP_ERROR"
    status_code = 400

    # 作用：保存用户可见消息和可选详情。
    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    """请求或业务校验失败。"""

    code = "VALIDATION_ERROR"
    status_code = 422


class AuthenticationError(AppError):
    """登录或令牌认证失败。"""

    code = "AUTHENTICATION_FAILED"
    status_code = 401


class AuthorizationError(AppError):
    """操作权限或数据权限拒绝。"""

    code = "AUTHORIZATION_DENIED"
    status_code = 403


class NotFoundError(AppError):
    """资源不存在。"""

    code = "RESOURCE_NOT_FOUND"
    status_code = 404


class ConflictError(AppError):
    """资源状态冲突。"""

    code = "RESOURCE_CONFLICT"
    status_code = 409


class DependencyUnavailableError(AppError):
    """外部依赖不可用且无法降级。"""

    code = "DEPENDENCY_UNAVAILABLE"
    status_code = 503
