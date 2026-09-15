"""提供四维数据权限适配器入口。"""

from kb_manage_platform.infrastructure.mysql.authorization_engine import MysqlAuthorizationEngine


class SqlAlchemyAuthorizer(MysqlAuthorizationEngine):
    """基于 MySQL 权限数据的四维候选鉴权适配器。"""


# 兼容旧名称；行为已由默认拒绝占位实现替换为真实鉴权。
DefaultDenyAuthorizer = SqlAlchemyAuthorizer