"""加载知识库平台配置，配置项来自 backend/.env。"""

from kb_manage_platform.bootstrap.settings import Settings, get_settings


class AppConfig:
    """应用配置门面，避免业务代码直接读取环境变量。"""

    # 作用：加载并保存类型化配置。
    def __init__(self) -> None:
        self.settings: Settings = get_settings()

    # 作用：返回当前应用配置对象。
    def get(self) -> Settings:
        """获取配置对象。"""
        return self.settings


# 作用：提供进程内共享配置门面，具体值仍由 pydantic-settings 读取。
app_config = AppConfig()