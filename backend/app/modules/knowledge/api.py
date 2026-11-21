"""经理使用的知识库维护 API；实际数据由 Agent Service 管理。"""

from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.modules.auth.dependencies import AuthContext, require_csrf, require_manager
from app.modules.auth.models import User
from app.modules.knowledge.schemas import (
    CreateKnowledgeDocumentRequest,
    KnowledgeDocumentList,
    KnowledgeIngestResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    MessageResponse,
)


router = APIRouter(prefix="/knowledge", tags=["knowledge-management"])
Manager = Annotated[User, Depends(require_manager)]


def _headers(manager: User) -> dict[str, str]:
    token = get_settings().agent_service_token
    if not token:
        raise HTTPException(status_code=503, detail="Agent service integration is not configured")
    return {
        "X-Agent-Service-Token": token,
        "X-Tenant-ID": str(manager.tenant_id),
        "X-User-ID": str(manager.id),
    }


async def _request(method: str, path: str, manager: User, json: Any = None) -> httpx.Response:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.agent_service_timeout_seconds) as client:
            response = await client.request(
                method,
                f"{settings.agent_service_url.rstrip('/')}{path}",
                headers=_headers(manager),
                json=json,
            )
    except httpx.RequestError as error:
        raise HTTPException(status_code=503, detail="Agent service is unavailable") from error
    if response.is_error:
        detail = "Knowledge service request failed"
        try:
            remote_detail = response.json().get("detail")
            if isinstance(remote_detail, str):
                detail = remote_detail
        except (ValueError, AttributeError):
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response


@router.get("/documents", response_model=KnowledgeDocumentList)
async def list_documents(manager: Manager) -> KnowledgeDocumentList:
    response = await _request("GET", "/knowledge/documents", manager)
    return KnowledgeDocumentList.model_validate(response.json())


@router.post("/documents", response_model=KnowledgeIngestResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: CreateKnowledgeDocumentRequest,
    _: Annotated[AuthContext, Depends(require_csrf)],
    manager: Manager,
) -> KnowledgeIngestResponse:
    response = await _request(
        "POST", "/knowledge/documents", manager, payload.model_dump(mode="json")
    )
    return KnowledgeIngestResponse.model_validate(response.json())


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    _: Annotated[AuthContext, Depends(require_csrf)],
    manager: Manager,
) -> KnowledgeSearchResponse:
    """代理当前经理所属租户的真实 RAG 检索，不接受前端 tenant_id。"""

    response = await _request(
        "POST", "/knowledge/search", manager, payload.model_dump(mode="json")
    )
    return KnowledgeSearchResponse.model_validate(response.json())


@router.delete("/documents/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: UUID,
    _: Annotated[AuthContext, Depends(require_csrf)],
    manager: Manager,
) -> MessageResponse:
    response = await _request("DELETE", f"/knowledge/documents/{document_id}", manager)
    return MessageResponse.model_validate(response.json())
