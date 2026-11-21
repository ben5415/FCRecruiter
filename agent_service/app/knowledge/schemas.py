"""知识入库与检索的类型化契约。"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class KnowledgeIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    source_uri: str = Field(min_length=1, max_length=1000)
    content: str = Field(min_length=1, max_length=2_000_000)
    tenant_id: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeIngestResult(BaseModel):
    document_id: UUID
    chunk_count: int = Field(ge=0)
    created: bool


class KnowledgeDocumentSummary(BaseModel):
    document_id: UUID
    title: str
    source_uri: str
    chunk_count: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class KnowledgeDocumentList(BaseModel):
    items: list[KnowledgeDocumentSummary]


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


class KnowledgeSearchResult(BaseModel):
    query: str
    hits: list[KnowledgeSearchHit]


class KnowledgeSearchRequest(BaseModel):
    """隐藏测试页使用的检索参数，不包含租户信息。"""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2_000)
    limit: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.25, ge=-1, le=1)


class KnowledgeSearchDebugResult(KnowledgeSearchResult):
    """真实 Embedding 与 pgvector 检索的结果及服务端总耗时。"""

    retrieval_ms: float = Field(ge=0)
