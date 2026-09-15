"""知识切片、Embedding、入库和检索编排。"""

import hashlib
from collections.abc import Callable

from sqlalchemy.orm import Session

from agent_service.app.knowledge.embeddings import EmbeddingAdapter
from agent_service.app.knowledge.repository import KnowledgeRepository, NewChunk
from agent_service.app.knowledge.schemas import (
    KnowledgeIngestRequest,
    KnowledgeIngestResult,
    KnowledgeDocumentSummary,
    KnowledgeSearchResult,
)


class KnowledgeService:
    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        embeddings: EmbeddingAdapter,
        chunk_size: int = 1200,
        chunk_overlap: int = 150,
    ) -> None:
        if chunk_size < 200:
            raise ValueError("chunk_size must be at least 200 characters")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be between 0 and chunk_size")
        self._session_factory = session_factory
        self._embeddings = embeddings
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def ingest(self, request: KnowledgeIngestRequest) -> KnowledgeIngestResult:
        normalized = request.content.strip()
        checksum = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        tenant_scope = request.tenant_id or 0
        with self._session_factory() as session:
            repository = KnowledgeRepository(session)
            existing = repository.find_document(tenant_scope, request.source_uri, checksum)
            if existing:
                return KnowledgeIngestResult(
                    document_id=existing.id,
                    chunk_count=len(existing.chunks),
                    created=False,
                )

        texts = split_text(normalized, self._chunk_size, self._chunk_overlap)
        vectors = await self._embeddings.embed_documents(texts)
        with self._session_factory() as session:
            repository = KnowledgeRepository(session)
            # Embedding 期间可能有另一个任务导入同一文档，因此写入前再次检查。
            existing = repository.find_document(tenant_scope, request.source_uri, checksum)
            if existing:
                return KnowledgeIngestResult(
                    document_id=existing.id,
                    chunk_count=len(existing.chunks),
                    created=False,
                )
            document = repository.create_document(
                tenant_scope=tenant_scope,
                title=request.title,
                source_uri=request.source_uri,
                checksum=checksum,
                metadata=request.metadata,
                chunks=[
                    NewChunk(
                        content=text,
                        token_estimate=max(1, (len(text) + 3) // 4),
                        metadata={"chunk_index": index},
                        embedding=vector,
                    )
                    for index, (text, vector) in enumerate(zip(texts, vectors, strict=True))
                ],
            )
            return KnowledgeIngestResult(
                document_id=document.id,
                chunk_count=len(texts),
                created=True,
            )

    def list_tenant_documents(self, tenant_id: int) -> list[KnowledgeDocumentSummary]:
        with self._session_factory() as session:
            return KnowledgeRepository(session).list_tenant_documents(tenant_id)

    def delete_tenant_document(self, tenant_id: int, document_id) -> bool:
        with self._session_factory() as session:
            return KnowledgeRepository(session).delete_tenant_document(tenant_id, document_id)

    async def search(
        self,
        *,
        query: str,
        tenant_id: int,
        limit: int = 5,
        min_similarity: float = 0.25,
    ) -> KnowledgeSearchResult:
        query_embedding = await self._embeddings.embed_query(query)
        with self._session_factory() as session:
            hits = KnowledgeRepository(session).search(
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                limit=limit,
                min_similarity=min_similarity,
            )
        return KnowledgeSearchResult(query=query, hits=hits)


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """按段落优先切片；超长段落按字符窗口切分，并保留少量重叠。"""

    paragraphs = [part.strip() for part in text.replace("\r\n", "\n").split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= chunk_size:
            current = paragraph
            continue
        step = chunk_size - overlap
        chunks.extend(paragraph[start:start + chunk_size] for start in range(0, len(paragraph), step))
        current = ""
    if current:
        chunks.append(current)
    return chunks or [text]
