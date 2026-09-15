"""短期 Memory 的 API/服务层数据契约。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_service.app.memory.models import MessageRole, ThreadStatus


class CreateThreadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_-]*$")
    title: str | None = Field(default=None, max_length=200)


class AppendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: MessageRole
    content: str = Field(min_length=1, max_length=100_000)
    tool_name: str | None = Field(default=None, max_length=64)
    tool_call_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_tool_fields(self) -> "AppendMessageRequest":
        if self.role == MessageRole.TOOL and not self.tool_call_id:
            raise ValueError("tool_call_id is required for tool messages")
        if self.role != MessageRole.TOOL and (self.tool_name or self.tool_call_id):
            raise ValueError("tool fields are only valid for tool messages")
        return self


class ThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: int
    user_id: int
    agent_key: str
    agent_version: int
    title: str | None
    status: ThreadStatus
    revision: int
    current_summary_version: int
    summarized_through_sequence: int
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    sequence: int
    role: MessageRole
    content: str
    tool_name: str | None
    tool_call_id: str | None
    metadata: dict[str, Any]
    created_at: datetime
    thread_revision: int


class SummaryResponse(BaseModel):
    thread_id: UUID
    version: int
    summarized_through_sequence: int
    content: str


class RollSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retain_recent_messages: int = Field(default=6, ge=2, le=50)
