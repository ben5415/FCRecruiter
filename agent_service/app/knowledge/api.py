"""由业务 Backend 调用的租户知识库维护接口。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from agent_service.app.api.dependencies import CallerIdentity, require_caller_identity
from agent_service.app.knowledge import build_knowledge_service_from_settings
from agent_service.app.knowledge.schemas import (
    KnowledgeDocumentList,
    KnowledgeIngestRequest,
    KnowledgeIngestResult,
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
    return await build_knowledge_service_from_settings().ingest(scoped)


@router.delete("/documents/{document_id}", response_model=MessageResponse)
async def delete_document(document_id: UUID, identity: Identity) -> MessageResponse:
    deleted = build_knowledge_service_from_settings().delete_tenant_document(
        identity.tenant_id, document_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    return MessageResponse(message="Knowledge document deleted")
