from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
