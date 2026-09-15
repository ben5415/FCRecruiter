"""Thread 创建、消息追加和 Memory 状态读取 API。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from agent_service.app.api.dependencies import CallerIdentity, require_caller_identity
from agent_service.app.memory.repository import (
    MemoryRepository,
    ThreadNotFoundError,
    ThreadVersionConflictError,
)
from agent_service.app.memory.schemas import (
    AppendMessageRequest,
    CreateThreadRequest,
    MessageResponse,
    ThreadResponse,
)
from agent_service.app.recruitment.prompt import RECRUITMENT_AGENT_KEY
from agent_service.app.registry.repository import ActiveAgentDefinitionNotFoundError, AgentDefinitionRepository
from agent_service.app.shared.database import get_agent_db_session


router = APIRouter(prefix="/threads", tags=["memory"])
Database = Annotated[Session, Depends(get_agent_db_session)]
Identity = Annotated[CallerIdentity, Depends(require_caller_identity)]


@router.post("", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(payload: CreateThreadRequest, identity: Identity, db: Database):
    if payload.agent_key != RECRUITMENT_AGENT_KEY:
        raise HTTPException(status_code=400, detail="Unsupported agent key")
    try:
        definition = AgentDefinitionRepository(db).discover_active(RECRUITMENT_AGENT_KEY)
    except ActiveAgentDefinitionNotFoundError as error:
        raise HTTPException(status_code=503, detail="Recruitment Agent has no active version") from error
    thread = MemoryRepository(db).create_thread(
        tenant_id=identity.tenant_id,
        user_id=identity.user_id,
        agent_key=RECRUITMENT_AGENT_KEY,
        agent_version=definition.version,
        title=payload.title,
    )
    return thread


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: UUID, identity: Identity, db: Database):
    try:
        return MemoryRepository(db).get_owned_thread(
            thread_id, identity.tenant_id, identity.user_id
        )
    except ThreadNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{thread_id}/messages", response_model=MessageResponse, status_code=201)
async def append_message(
    thread_id: UUID,
    payload: AppendMessageRequest,
    identity: Identity,
    db: Database,
):
    try:
        message, revision = MemoryRepository(db).append_message(
            thread_id=thread_id,
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            role=payload.role,
            content=payload.content,
            tool_name=payload.tool_name,
            tool_call_id=payload.tool_call_id,
            metadata=payload.metadata,
            expected_revision=payload.expected_revision,
        )
    except ThreadNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ThreadVersionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return MessageResponse(
        id=message.id,
        thread_id=message.thread_id,
        sequence=message.sequence,
        role=message.role,
        content=message.content,
        tool_name=message.tool_name,
        tool_call_id=message.tool_call_id,
        metadata=message.message_metadata,
        created_at=message.created_at,
        thread_revision=revision,
    )
