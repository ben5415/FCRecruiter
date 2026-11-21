from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PythonEnum
from typing import Any

from sqlalchemy import DateTime, Enum, Index, Integer, JSON, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from agent_service.app.shared.database import Base


class AgentDefinitionStatus(str, PythonEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"


class AgentDefinition(Base):
    __tablename__ = "agent_definitions"
    __table_args__ = (
        UniqueConstraint("agent_key", "version", name="uq_agent_definition_key_version"),
        Index("ix_agent_definitions_agent_key", "agent_key"),
        Index(
            "uq_agent_definition_one_active", "agent_key", unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    agent_key: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tool_names: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[AgentDefinitionStatus] = mapped_column(
        Enum(AgentDefinitionStatus, name="agent_definition_status", values_callable=lambda values: [v.value for v in values]),
        nullable=False, default=AgentDefinitionStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

