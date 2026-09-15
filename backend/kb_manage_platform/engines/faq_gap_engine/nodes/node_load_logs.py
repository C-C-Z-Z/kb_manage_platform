"""加载 FAQ 挖掘和知识缺口识别所需日志。"""

from typing import Any

from kb_manage_platform.domain.ports import QaLogRepositoryPort
from kb_manage_platform.engines.faq_gap_engine.base import FaqGapNodeBase
from kb_manage_platform.engines.faq_gap_engine.state import FaqGapGraphState


class NodeLoadQaLogs(FaqGapNodeBase):
    """读取问答审计日志。"""

    name = "node_load_qa_logs"

    # 作用：保存问答日志仓储。
    def __init__(self, repository: QaLogRepositoryPort) -> None:
        self._repository = repository

    # 作用：读取指定窗口日志。
    async def process(self, state: FaqGapGraphState) -> dict[str, Any]:
        """返回日志集合。"""
        command = state["command"]
        logs = await self._repository.list_logs(command.window_days)
        return {"logs": tuple(logs)}