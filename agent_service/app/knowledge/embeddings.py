"""Embedding Provider 适配层。

默认通过 Ollama 在本机生成向量，也保留其他 Provider 实现。
测试可注入 Fake EmbeddingAdapter，避免下载模型或产生网络调用。
"""

import asyncio
from collections.abc import Sequence
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict


class EmbeddingAdapter(Protocol):
    @property
    def dimensions(self) -> int: ...

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class _EmbeddingItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    index: int
    embedding: list[float]


class _EmbeddingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: list[_EmbeddingItem]


class _OllamaEmbeddingResponse(BaseModel):
    """Ollama `/api/embed` 返回结构中本项目需要的字段。"""

    model_config = ConfigDict(extra="ignore")
    embeddings: list[list[float]]


class OllamaEmbeddingAdapter:
    """通过 Ollama 的本机 HTTP API 生成 Embedding。

    适配器只负责协议转换与响应校验。知识切片、数据库查询等业务逻辑
    仍留在 KnowledgeService 中，因此以后更换模型不会影响上层代码。
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        dimensions: int,
        timeout_seconds: float = 60,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_url = f"{base_url.rstrip('/')}/api/embed"
        self._model = model
        self._dimensions = dimensions
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        async def send(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(
                self._api_url,
                json={"model": self._model, "input": list(texts)},
                timeout=self._timeout_seconds,
            )

        if self._http_client is not None:
            response = await send(self._http_client)
        else:
            async with httpx.AsyncClient() as client:
                response = await send(client)

        response.raise_for_status()
        parsed = _OllamaEmbeddingResponse.model_validate(response.json())
        if len(parsed.embeddings) != len(texts):
            raise ValueError("Ollama returned an unexpected embedding count")
        if any(len(vector) != self._dimensions for vector in parsed.embeddings):
            raise ValueError("Ollama embedding dimensions do not match the database schema")
        return parsed.embeddings

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]


class OpenAICompatibleEmbeddingAdapter:
    def __init__(
        self,
        *,
        api_url: str,
        api_key: str,
        model: str,
        dimensions: int,
        timeout_seconds: float = 20,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {"model": self._model, "input": list(texts)}

        async def send(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(
                self._api_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
                timeout=self._timeout_seconds,
            )

        if self._http_client is not None:
            response = await send(self._http_client)
        else:
            async with httpx.AsyncClient() as client:
                response = await send(client)
        response.raise_for_status()
        parsed = _EmbeddingResponse.model_validate(response.json())
        ordered = [item.embedding for item in sorted(parsed.data, key=lambda item: item.index)]
        if len(ordered) != len(texts):
            raise ValueError("Embedding provider returned an unexpected item count")
        if any(len(vector) != self._dimensions for vector in ordered):
            raise ValueError("Embedding dimensions do not match the database schema")
        return ordered

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]


class LocalSentenceTransformerEmbeddingAdapter:
    """在本机运行 Sentence Transformers，不产生按次 API 费用。

    E5 系列训练时区分 query/passage 前缀，因此查询和知识片段分别加前缀。
    encode 是同步且消耗 CPU 的调用，通过 asyncio.to_thread 避免阻塞事件循环。
    """

    def __init__(
        self,
        *,
        model_name: str,
        dimensions: int,
        device: str = "cpu",
        model_instance: Any | None = None,
    ) -> None:
        if model_instance is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise RuntimeError(
                    "sentence-transformers is required for local embeddings"
                ) from error
            model_instance = SentenceTransformer(model_name, device=device)
        actual_dimensions = model_instance.get_sentence_embedding_dimension()
        if actual_dimensions != dimensions:
            raise ValueError(
                f"Local model returns {actual_dimensions} dimensions, expected {dimensions}"
            )
        self._model = model_instance
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        def encode() -> Any:
            return self._model.encode(
                list(texts),
                normalize_embeddings=True,
                show_progress_bar=False,
            )

        vectors = await asyncio.to_thread(encode)
        result = [[float(value) for value in vector] for vector in vectors]
        if any(len(vector) != self._dimensions for vector in result):
            raise ValueError("Local embedding dimensions do not match the database schema")
        return result

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._encode([f"passage: {text}" for text in texts])

    async def embed_query(self, text: str) -> list[float]:
        return (await self._encode([f"query: {text}"]))[0]
