"""提供审计日志适配器入口。"""

from kb_manage_platform.infrastructure.mysql.audit_repository import MysqlAuditLogger


class SqlAlchemyAuditLogger(MysqlAuditLogger):
    """基于 MySQL 的审计日志适配器。"""


# 兼容旧名称；行为已由空操作占位实现替换为持久化审计。
NoopAuditLogger = SqlAlchemyAuditLogger