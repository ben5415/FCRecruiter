"""知识文档持久化与固定 pgvector 余弦检索。"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from agent_service.app.knowledge.models import KnowledgeChunk, KnowledgeDocument
from agent_service.app.knowledge.schemas import KnowledgeDocumentSummary, KnowledgeSearchHit


@dataclass(frozen=True)
class NewChunk:
    content: str
    token_estimate: int
    metadata: dict
    embedding: list[float]


class KnowledgeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_document(self, tenant_scope: int, source_uri: str, checksum: str) -> KnowledgeDocument | None:
        return self._session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.tenant_scope == tenant_scope,
                KnowledgeDocument.source_uri == source_uri,
                KnowledgeDocument.checksum == checksum,
            )
        )

    def create_document(
        self,
        *,
        tenant_scope: int,
        title: str,
        source_uri: str,
        checksum: str,
        metadata: dict,
        chunks: list[NewChunk],
    ) -> KnowledgeDocument:
        document = KnowledgeDocument(
            tenant_scope=tenant_scope,
            title=title,
            source_uri=source_uri,
            checksum=checksum,
            document_metadata=metadata,
        )
        self._session.add(document)
        self._session.flush()
        self._session.add_all([
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk.content,
                token_estimate=chunk.token_estimate,
                chunk_metadata=chunk.metadata,
                embedding=chunk.embedding,
            )
            for index, chunk in enumerate(chunks)
        ])
        self._session.commit()
        self._session.refresh(document)
        return document

    def list_tenant_documents(self, tenant_id: int) -> list[KnowledgeDocumentSummary]:
        rows = self._session.execute(
            select(KnowledgeDocument, func.count(KnowledgeChunk.id))
            .outerjoin(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeDocument.tenant_scope == tenant_id)
            .group_by(KnowledgeDocument.id)
            .order_by(KnowledgeDocument.created_at.desc(), KnowledgeDocument.id)
        ).all()
        return [KnowledgeDocumentSummary(
            document_id=document.id,
            title=document.title,
            source_uri=document.source_uri,
            chunk_count=chunk_count,
            metadata=document.document_metadata,
            created_at=document.created_at,
        ) for document, chunk_count in rows]

    def delete_tenant_document(self, tenant_id: int, document_id: UUID) -> bool:
        document = self._session.scalar(select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_scope == tenant_id,
        ))
        if document is None:
            return False
        self._session.delete(document)
        self._session.commit()
        return True

    def search(
        self,
        *,
        query_embedding: list[float],
        tenant_id: int,
        limit: int,
        min_similarity: float,
    ) -> list[KnowledgeSearchHit]:
        distance = KnowledgeChunk.embedding.cosine_distance(query_embedding).label("distance")
        rows = self._session.execute(
            select(KnowledgeChunk, KnowledgeDocument, distance)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(or_(
                KnowledgeDocument.tenant_scope == 0,
                KnowledgeDocument.tenant_scope == tenant_id,
            ))
            .order_by(distance)
            .limit(limit)
        ).all()
        hits: list[KnowledgeSearchHit] = []
        for chunk, document, raw_distance in rows:
            similarity = 1.0 - float(raw_distance)
            if similarity < min_similarity:
                continue
            hits.append(KnowledgeSearchHit(
                chunk_id=chunk.id,
                document_id=document.id,
                title=document.title,
                source_uri=document.source_uri,
                content=chunk.content,
                similarity=similarity,
                chunk_index=chunk.chunk_index,
                metadata={**document.document_metadata, **chunk.chunk_metadata},
            ))
        return hits
