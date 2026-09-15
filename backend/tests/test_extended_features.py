"""扩展 PRD 功能的单元测试。"""

import pytest

from kb_manage_platform.bootstrap.settings import Settings
from types import SimpleNamespace

from kb_manage_platform.domain.models import RetrievedCandidate, UserContext
from kb_manage_platform.domain.services.permissions import PermissionPolicy
from kb_manage_platform.infrastructure.adapters.secret_utils import LocalSecretCipher
from kb_manage_platform.engines.query_engine.nodes.node_answer_output import NodeAnswerOutput
from kb_manage_platform.infrastructure.mysql.authorization_engine import MysqlAuthorizationEngine
from kb_manage_platform.services.configuration_service import ConfigurationService


class FakeAudit:
    async def record(self, event_type, payload):
        return None


class FakeModelRepository:
    async def list_all(self):
        return ()

    async def get(self, model_type):
        return None


class FakeSettingRepository:
    async def list_all(self):
        return ()


class FakeCipher(LocalSecretCipher):
    pass


def test_local_secret_cipher_roundtrip() -> None:
    cipher = LocalSecretCipher("test-secret")
    encrypted = cipher.encrypt("sk-example-secret-key")
    assert encrypted != "sk-example-secret-key"
    assert cipher.decrypt(encrypted) == "sk-example-secret-key"
    assert cipher.mask("sk-example-secret-key").startswith("sk-e")
    assert cipher.mask("sk-example-secret-key").endswith("-key")


@pytest.mark.asyncio
async def test_configuration_service_exposes_local_embedding_defaults() -> None:
    settings = Settings(
        bge_m3="BAAI/bge-m3",
        bge_m3_path="D:/models/bge-m3",
        bge_device="cpu",
        bge_fp16=False,
        openai_api_key="llm-key",
        embedding_api_key="embedding-key",
    )
    service = ConfigurationService(
        settings,
        FakeModelRepository(),
        FakeSettingRepository(),
        LocalSecretCipher("test-secret"),
        FakeAudit(),
    )
    models = await service.list_models()
    embedding = next(item for item in models if item["model_type"] == "embedding")
    assert embedding["model_name"] == "BAAI/bge-m3"
    assert embedding["local_model_path"] == "D:/models/bge-m3"
    assert embedding["options"]["device"] == "cpu"
    assert embedding["api_key_masked"] != "embedding-key"


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeAuthorizationSession:
    def __init__(self, responses):
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def scalars(self, statement):
        return FakeScalarResult(self._responses.pop(0))


class FakeAuthorizationSessionFactory:
    def __init__(self, responses):
        self._responses = responses

    def __call__(self):
        return FakeAuthorizationSession(self._responses)


@pytest.mark.asyncio
async def test_authorization_engine_allows_global_candidate() -> None:
    permission = SimpleNamespace(
        knowledge_id="sample-kb-travel",
        scope="global",
        subject_id="",
        include_descendants=False,
    )
    unit = SimpleNamespace(
        knowledge_id="sample-kb-travel",
        current_version_id="version-sample-kb-travel",
    )
    version = SimpleNamespace(version_id="version-sample-kb-travel")
    engine = MysqlAuthorizationEngine(
        FakeAuthorizationSessionFactory([[permission], [unit], [version]]),
        PermissionPolicy(),
    )
    candidate = RetrievedCandidate(
        chunk_id="chunk-1",
        knowledge_id="sample-kb-travel",
        version_id="version-sample-kb-travel",
        content="差旅报销材料",
        score=1.0,
        source="test",
    )
    user = UserContext(
        user_id="user-admin",
        department_id="dept-root",
        role_ids=("role-system-admin",),
        permission_version=1,
    )
    allowed = await engine.filter_allowed(user, [candidate])
    assert len(allowed) == 1
    assert allowed[0].chunk_id == candidate.chunk_id
    assert allowed[0].metadata["permission_signature"] == "global"


class FailingAnswerGenerator:
    async def generate(self, question, candidates, history=()):
        raise RuntimeError("llm unavailable")


@pytest.mark.asyncio
async def test_answer_output_uses_extractive_fallback() -> None:
    node = NodeAnswerOutput(FailingAnswerGenerator())
    candidate = RetrievedCandidate(
        chunk_id="chunk-1",
        knowledge_id="sample-kb-travel",
        version_id="version-1",
        content="报销需要发票、行程单和审批记录。",
        score=1.0,
        source="test",
    )
    state = {
        "normalized_question": "差旅报销需要哪些材料？",
        "final_candidates": [candidate],
        "request": SimpleNamespace(history=()),
    }
    result = await node.process(state)
    answer = result["answer"]
    assert "报销需要发票" in answer.answer
    assert answer.citations == (candidate,)
    assert "llm_unavailable_extractive_fallback" in answer.warnings
