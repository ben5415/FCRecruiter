"""Thread、Message 与滚动摘要的持久化模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PythonEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_service.app.shared.database import Base


class ThreadStatus(str, PythonEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MessageRole(str, PythonEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ConversationThread(Base):
    __tablename__ = "conversation_threads"
    __table_args__ = (
        Index("ix_conversation_threads_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    agent_key: Mapped[str] = mapped_column(String(80), nullable=False)
    agent_version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[ThreadStatus] = mapped_column(
        Enum(ThreadStatus, name="thread_status", values_callable=lambda values: [v.value for v in values]),
        nullable=False,
        default=ThreadStatus.ACTIVE,
    )
    # revision 用于乐观锁：客户端只能在自己读到的版本上追加消息。
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_summary_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summarized_through_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list[ConversationMessage]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )
    summaries: Mapped[list[ThreadSummary]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint("thread_id", "sequence", name="uq_message_thread_sequence"),
        Index("ix_conversation_messages_thread_sequence", "thread_id", "sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conversation_threads.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", values_callable=lambda values: [v.value for v in values]),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(64))
    tool_call_id: Mapped[str | None] = mapped_column(String(128))
    message_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped[ConversationThread] = relationship(back_populates="messages")


class ThreadSummary(Base):
    __tablename__ = "thread_summaries"
    __table_args__ = (
        UniqueConstraint("thread_id", "version", name="uq_thread_summary_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conversation_threads.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    summarized_through_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped[ConversationThread] = relationship(back_populates="summaries")
