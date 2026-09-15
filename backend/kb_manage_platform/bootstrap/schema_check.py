"""校验 MySQL 实际 Schema 与 SQLAlchemy 模型一致。"""

from sqlalchemy import inspect

from kb_manage_platform.infrastructure.mysql.base import Base
from kb_manage_platform.infrastructure.mysql.models import *  # noqa: F403
from kb_manage_platform.infrastructure.mysql.session import Database


async def check_schema(database: Database) -> None:
    """缺表或缺列时立即失败，避免运行期出现半迁移状态。"""

    def inspect_schema(sync_connection) -> list[str]:
        inspector = inspect(sync_connection)
        actual_tables = set(inspector.get_table_names())
        problems: list[str] = []
        for table in Base.metadata.sorted_tables:
            if table.name not in actual_tables:
                problems.append(f"missing table: {table.name}")
                continue
            actual_columns = {column["name"] for column in inspector.get_columns(table.name)}
            expected_columns = {column.name for column in table.columns}
            for name in sorted(expected_columns - actual_columns):
                problems.append(f"missing column: {table.name}.{name}")
        return problems

    async with database.engine.connect() as connection:
        problems = await connection.run_sync(inspect_schema)
    if problems:
        raise RuntimeError("database schema mismatch: " + "; ".join(problems))
