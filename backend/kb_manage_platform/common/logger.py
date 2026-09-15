"""提供统一的日志记录器。"""

import logging


class LoggerFactory:
    """创建并配置应用日志记录器。"""

    # 作用：按指定名称和级别创建日志记录器。
    @staticmethod
    def create(name: str = "kb_manage") -> logging.Logger:
        """创建日志记录器。"""
        logger = logging.getLogger(name)
        if logger.handlers:
            return logger
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.propagate = False
        return logger


# 作用：提供全局日志对象供节点和 Web 层复用。
logger = LoggerFactory.create()