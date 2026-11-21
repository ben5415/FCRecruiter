"""由业务 Backend 调用的租户知识库维护与测试接口。"""

from time import perf_counter
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from agent_service.app.api.dependencies import CallerIdentity, require_caller_identity
from agent_service.app.knowledge import build_knowledge_service_from_settings
from agent_service.app.knowledge.embeddings import (
    EmbeddingProviderError,
    EmbeddingProviderUnavailableError,
)
from agent_service.app.knowledge.schemas import (
    KnowledgeDocumentList,
    KnowledgeIngestRequest,
    KnowledgeIngestResult,
    KnowledgeSearchDebugResult,
    KnowledgeSearchRequest,
)


router = APIRouter(prefix="/knowledge", tags=["knowledge-management"])
Identity = Annotated[CallerIdentity, Depends(require_caller_identity)]


class MessageResponse(BaseModel):
    message: str


@router.get("/documents", response_model=KnowledgeDocumentList)
async def list_documents(identity: Identity) -> KnowledgeDocumentList:
    items = build_knowledge_service_from_settings().list_tenant_documents(identity.tenant_id)
    return KnowledgeDocumentList(items=items)


@router.post("/documents", response_model=KnowledgeIngestResult, status_code=status.HTTP_201_CREATED)
async def create_document(payload: KnowledgeIngestRequest, identity: Identity) -> KnowledgeIngestResult:
    # tenant_id 永远由可信请求头注入，忽略/覆盖请求正文中的租户范围。
    scoped = payload.model_copy(update={"tenant_id": identity.tenant_id})
    try:
        return await build_knowledge_service_from_settings().ingest(scoped)
    except EmbeddingProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Embedding service is unavailable. Start Ollama and make sure "
                "OLLAMA_BASE_URL is reachable from Agent Service."
            ),
        ) from error
    except EmbeddingProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding service returned an invalid response.",
        ) from error


@router.post("/search", response_model=KnowledgeSearchDebugResult)
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    identity: Identity,
) -> KnowledgeSearchDebugResult:
    """运行真实租户检索，供未加入导航的 RAG 测试页使用。"""

    started = perf_counter()
    try:
        result = await build_knowledge_service_from_settings().search(
            query=payload.query,
            tenant_id=identity.tenant_id,
            limit=payload.limit,
            min_similarity=payload.min_similarity,
        )
    except EmbeddingProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Embedding service is unavailable. Start Ollama and make sure "
                "OLLAMA_BASE_URL is reachable from Agent Service."
            ),
        ) from error
    except EmbeddingProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding service returned an invalid response.",
        ) from error
    return KnowledgeSearchDebugResult(
        query=result.query,
        hits=result.hits,
        retrieval_ms=round((perf_counter() - started) * 1000, 2),
    )


@router.delete("/documents/{document_id}", response_model=MessageResponse)
async def delete_document(document_id: UUID, identity: Identity) -> MessageResponse:
    deleted = build_knowledge_service_from_settings().delete_tenant_document(
        identity.tenant_id, document_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    return MessageResponse(message="Knowledge document deleted")
