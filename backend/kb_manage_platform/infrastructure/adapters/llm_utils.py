"""实现基于 LangChain 和 OpenAI 兼容接口的 LLM HyDE 与回答生成。"""

import json
import re
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from kb_manage_platform.domain.models import AnswerResult, ConversationMessage, RetrievedCandidate


class LangChainHydeGenerator:
    """使用 LangChain ChatOpenAI 生成 HyDE 假设文档。"""

    # 作用：创建 LangChain LLM 客户端并保存 HyDE 参数。
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: int,
    ) -> None:
        self._llm = self._build_client(
            api_key,
            base_url,
            model,
            temperature,
            max_tokens,
            timeout_seconds,
        )

    # 作用：在不重启进程的情况下切换模型配置。
    def configure(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: int,
    ) -> None:
        self._llm = self._build_client(
            api_key,
            base_url,
            model,
            temperature,
            max_tokens,
            timeout_seconds,
        )

    # 作用：构造 LangChain OpenAI 兼容客户端。
    @staticmethod
    def _build_client(
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: int,
    ) -> ChatOpenAI:
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout_seconds,
        )

    # 作用：根据原问题生成一个或多个假设性答案。
    async def generate(self, question: str, count: int) -> Sequence[str]:
        """返回去除重复后的 HyDE 文档列表。"""
        requested_count = max(1, count)
        response = await self._llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是企业知识库检索助手。请生成可以被检索到的假设性答案文档，"
                        "只输出 JSON 字符串数组，不要解释数组本身。"
                    )
                ),
                HumanMessage(
                    content=(
                        f"用户问题：{question}\n"
                        f"请生成 {requested_count} 个语义互补、事实风格的中文假设文档。"
                    )
                ),
            ]
        )
        documents = self._parse_documents(_message_text(response.content), requested_count)
        if not documents:
            raise RuntimeError("LLM returned no HyDE document")
        return documents

    # 作用：解析 LLM 返回的 JSON 数组，并兼容简单列表文本。
    def _parse_documents(self, content: str, count: int) -> list[str]:
        """从模型文本中恢复 HyDE 文档。"""
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                parsed = parsed.get("documents", [])
            if isinstance(parsed, list):
                documents = [str(item).strip() for item in parsed if str(item).strip()]
                return list(dict.fromkeys(documents))[:count]
        except json.JSONDecodeError:
            pass
        lines = [
            re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
            for line in content.splitlines()
        ]
        return [line for line in dict.fromkeys(lines) if line][:count]


class LangChainAnswerGenerator:
    """使用 LangChain ChatOpenAI 严格基于授权知识生成回答。"""

    # 作用：创建最终回答使用的 LangChain LLM 客户端。
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: int,
    ) -> None:
        self._llm = self._build_client(
            api_key,
            base_url,
            model,
            temperature,
            max_tokens,
            timeout_seconds,
        )

    # 作用：在不重启进程的情况下切换模型配置。
    def configure(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: int,
    ) -> None:
        self._llm = self._build_client(
            api_key,
            base_url,
            model,
            temperature,
            max_tokens,
            timeout_seconds,
        )

    # 作用：构造 LangChain OpenAI 兼容客户端。
    @staticmethod
    def _build_client(
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: int,
    ) -> ChatOpenAI:
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout_seconds,
        )

    # 作用：仅根据已授权候选和会话历史生成回答。
    async def generate(
        self,
        question: str,
        candidates: Sequence[RetrievedCandidate],
        history: Sequence[ConversationMessage] = (),
    ) -> AnswerResult:
        """返回回答正文及其引用切片。"""
        if not candidates:
            return AnswerResult(answer="现有知识无法支撑该问题。", warnings=("no_authorized_context",))
        messages: list[BaseMessage] = [
            SystemMessage(
                content=(
                    "你是企业知识库问答助手。只能使用给定知识片段回答，禁止补充片段之外的"
                    "通用知识。若片段不足，应明确回答“现有知识无法支撑该问题”。回答中的关键"
                    "事实必须使用 [S1]、[S2] 形式标注来源。"
                )
            )
        ]
        messages.extend(self._history_messages(history))
        messages.append(
            HumanMessage(
                content=(
                    f"用户问题：{question}\n\n"
                    f"授权知识片段：\n{self._build_context(candidates)}\n\n"
                    "请给出严谨、简洁且带来源标记的回答。"
                )
            )
        )
        response = await self._llm.ainvoke(messages)
        answer = _message_text(response.content).strip()
        if not answer:
            raise RuntimeError("LLM returned an empty answer")
        citations = self._extract_citations(answer, candidates)
        return AnswerResult(answer=answer, citations=citations)

    # 作用：将历史消息转换为 LangChain 消息类型。
    def _history_messages(self, history: Sequence[ConversationMessage]) -> list[BaseMessage]:
        """返回最近会话消息。"""
        messages: list[BaseMessage] = []
        for item in history[-10:]:
            if item.role == "assistant":
                messages.append(AIMessage(content=item.content))
            elif item.role == "user":
                messages.append(HumanMessage(content=item.content))
        return messages

    # 作用：拼装带编号的授权知识上下文。
    def _build_context(self, candidates: Sequence[RetrievedCandidate]) -> str:
        """返回模型使用的引用上下文。"""
        blocks = []
        for index, candidate in enumerate(candidates, start=1):
            content = candidate.content.strip()
            if len(content) > 4000:
                content = f"{content[:4000]}..."
            blocks.append(
                f"[S{index}] 知识ID={candidate.knowledge_id} 切片ID={candidate.chunk_id}\n{content}"
            )
        return "\n\n".join(blocks)

    # 作用：按回答中的来源标记筛选引用。
    def _extract_citations(
        self,
        answer: str,
        candidates: Sequence[RetrievedCandidate],
    ) -> tuple[RetrievedCandidate, ...]:
        """返回回答实际引用的候选，无法解析时保留全部候选。"""
        indexes = sorted({int(value) for value in re.findall(r"\[S(\d+)\]", answer)})
        citations = [candidates[index - 1] for index in indexes if 0 < index <= len(candidates)]
        return tuple(citations or candidates)


# 作用：提取 LangChain 消息中的纯文本。
def _message_text(content: Any) -> str:
    """兼容字符串和内容块列表两种消息格式。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    return str(content or "")