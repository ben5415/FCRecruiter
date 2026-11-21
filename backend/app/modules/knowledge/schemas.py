from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class CreateKnowledgeDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    source_uri: str = Field(min_length=1, max_length=1000)
    content: str = Field(min_length=1, max_length=2_000_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeDocumentSummary(BaseModel):
    document_id: UUID
    title: str
    source_uri: str
    chunk_count: int
    metadata: dict[str, Any]
    created_at: datetime


class KnowledgeDocumentList(BaseModel):
    items: list[KnowledgeDocumentSummary]


class KnowledgeIngestResponse(BaseModel):
    document_id: UUID
    chunk_count: int
    created: bool


class MessageResponse(BaseModel):
    message: str


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2_000)
    limit: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.25, ge=-1, le=1)


class KnowledgeSearchHit(BaseModel):
    chunk_id: UUID
    document_id: UUID
    title: str
    source_uri: str
    content: str
    similarity: float = Field(ge=-1, le=1)
    chunk_index: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def evidence_source_id(self) -> str:
        return f"knowledge:{self.chunk_id}"


class KnowledgeSearchResponse(BaseModel):
    query: str
    hits: list[KnowledgeSearchHit]
    retrieval_ms: float = Field(ge=0)
