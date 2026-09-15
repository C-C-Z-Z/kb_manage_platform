"""实现 HTTP Reranker 精排适配器。"""

from collections.abc import Sequence
from dataclasses import replace

import httpx

from kb_manage_platform.domain.models import RetrievedCandidate


class ModelReranker:
    """调用独立 Reranker 模型对候选知识进行二次排序。"""

    # 作用：保存 Reranker 接口和模型参数。
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        instruct: str = "",
        timeout_seconds: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._instruct = instruct
        self._timeout_seconds = timeout_seconds

    # 作用：在不重启进程的情况下切换 Reranker 配置。
    def configure(
        self,
        base_url: str,
        api_key: str,
        model: str,
        instruct: str = "",
        timeout_seconds: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._instruct = instruct
        self._timeout_seconds = timeout_seconds

    # 作用：根据用户问题重排 RRF 候选。
    async def rerank(
        self,
        question: str,
        candidates: Sequence[RetrievedCandidate],
        top_k: int,
    ) -> Sequence[RetrievedCandidate]:
        """返回相关性分数降序的候选列表。"""
        if not candidates:
            return []
        self._validate_config()
        endpoint = self._endpoint()
        payload = self._payload(question, candidates, top_k, endpoint)
        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout_seconds)) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        results = self._extract_results(body)
        reranked: list[RetrievedCandidate] = []
        for item in results:
            index = int(item.get("index", -1))
            if 0 <= index < len(candidates):
                score = float(item.get("relevance_score", item.get("score", 0.0)))
                reranked.append(replace(candidates[index], score=score, source=f"{candidates[index].source}+rerank"))
        if not reranked:
            raise RuntimeError("reranker returned no valid result")
        reranked.sort(key=lambda candidate: candidate.score, reverse=True)
        return reranked[: max(1, top_k)]

    # 作用：校验 Reranker 配置。
    def _validate_config(self) -> None:
        """阻止使用占位模型或空地址发起请求。"""
        if not self._base_url or not self._model or self._model.upper().startswith("CHANGE_ME"):
            raise RuntimeError("reranker model is not configured")

    # 作用：构造 Reranker 请求地址。
    def _endpoint(self) -> str:
        """兼容标准 /rerank 和 DashScope 文本重排地址。"""
        if self._base_url.endswith("/rerank") or "/services/rerank/" in self._base_url:
            return self._base_url
        return f"{self._base_url}/rerank"

    # 作用：根据服务类型构造请求体。
    def _payload(self, question, candidates, top_k, endpoint):
        """返回标准或 DashScope 重排请求体。"""
        top_n = min(max(1, top_k), len(candidates))
        if "/services/rerank/" in endpoint:
            return {
                "model": self._model,
                "input": {
                    "query": question,
                    "documents": [candidate.content for candidate in candidates],
                },
                "parameters": {"return_documents": False, "top_n": top_n},
            }
        payload: dict[str, object] = {
            "model": self._model,
            "query": question,
            "documents": [candidate.content for candidate in candidates],
            "top_n": top_n,
            "return_documents": False,
        }
        if self._instruct:
            payload["instruct"] = self._instruct
        return payload

    # 作用：兼容常见 Reranker 响应结构。
    @staticmethod
    def _extract_results(body: dict[str, object]) -> list[dict[str, object]]:
        """返回包含 index 和 score 的结果列表。"""
        output = body.get("output", {})
        if isinstance(output, dict) and isinstance(output.get("results"), list):
            return output["results"]
        if isinstance(body.get("results"), list):
            return body["results"]
        data = body.get("data", {})
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            return data["results"]
        return []