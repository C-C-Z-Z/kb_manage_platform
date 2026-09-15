"""验证权限过滤后的回答提示。"""

from types import SimpleNamespace

import pytest

from kb_manage_platform.domain.models import AnswerResult, RetrievedCandidate
from kb_manage_platform.engines.query_engine.nodes.node_answer_output import (
    PERMISSION_RESTRICTED_NOTICE,
    PERMISSION_RESTRICTED_WARNING,
    NodeAnswerOutput,
)


class StaticAnswerGenerator:
    async def generate(self, question, candidates, history=()):
        return AnswerResult(answer="这是基于授权知识的回答。", citations=tuple(candidates))


class UnexpectedAnswerGenerator:
    async def generate(self, question, candidates, history=()):
        raise AssertionError("没有授权候选时不应调用回答生成器")


def candidate(chunk_id: str, knowledge_id: str, content: str = "参考内容") -> RetrievedCandidate:
    return RetrievedCandidate(
        chunk_id=chunk_id,
        knowledge_id=knowledge_id,
        version_id=f"{knowledge_id}-v1",
        content=content,
        score=1.0,
        source="test",
    )


@pytest.mark.asyncio
async def test_answer_marks_permission_restricted_recall() -> None:
    allowed = candidate("chunk-allowed", "knowledge-allowed")
    blocked = candidate("chunk-blocked", "knowledge-blocked")
    state = {
        "normalized_question": "测试问题",
        "request": SimpleNamespace(history=()),
        "rrf_candidates": [allowed, blocked],
        "allowed_candidates": [allowed],
        "final_candidates": [allowed],
    }

    result = await NodeAnswerOutput(StaticAnswerGenerator()).process(state)
    answer = result["answer"]

    assert PERMISSION_RESTRICTED_NOTICE in answer.answer
    assert answer.answer.endswith(PERMISSION_RESTRICTED_NOTICE)
    assert PERMISSION_RESTRICTED_WARNING in answer.warnings


@pytest.mark.asyncio
async def test_answer_marks_when_all_recall_is_restricted() -> None:
    blocked = candidate("chunk-blocked", "knowledge-blocked")
    state = {
        "normalized_question": "测试问题",
        "request": SimpleNamespace(history=()),
        "rrf_candidates": [blocked],
        "allowed_candidates": [],
        "final_candidates": [],
    }

    result = await NodeAnswerOutput(UnexpectedAnswerGenerator()).process(state)
    answer = result["answer"]

    assert "no_authorized_context" in answer.warnings
    assert PERMISSION_RESTRICTED_WARNING in answer.warnings
    assert PERMISSION_RESTRICTED_NOTICE in answer.answer


@pytest.mark.asyncio
async def test_answer_does_not_claim_permission_restriction_when_authorization_unavailable() -> None:
    recalled = candidate("chunk-1", "knowledge-1")
    state = {
        "normalized_question": "测试问题",
        "request": SimpleNamespace(history=()),
        "rrf_candidates": [recalled],
        "allowed_candidates": [],
        "final_candidates": [],
        "warnings": ["authorization_unavailable_default_deny"],
    }

    result = await NodeAnswerOutput(UnexpectedAnswerGenerator()).process(state)
    answer = result["answer"]

    assert PERMISSION_RESTRICTED_NOTICE not in answer.answer
    assert PERMISSION_RESTRICTED_WARNING not in answer.warnings


@pytest.mark.asyncio
async def test_answer_does_not_mark_when_all_recall_is_authorized() -> None:
    allowed = candidate("chunk-allowed", "knowledge-allowed")
    state = {
        "normalized_question": "测试问题",
        "request": SimpleNamespace(history=()),
        "rrf_candidates": [allowed],
        "allowed_candidates": [allowed],
        "final_candidates": [allowed],
    }

    result = await NodeAnswerOutput(StaticAnswerGenerator()).process(state)
    answer = result["answer"]

    assert PERMISSION_RESTRICTED_NOTICE not in answer.answer
    assert PERMISSION_RESTRICTED_WARNING not in answer.warnings