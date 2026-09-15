import asyncio

from langchain_core.messages import SystemMessage
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from agent_service.app.memory.context import MemoryContextBuilder
from agent_service.app.memory.models import MessageRole, ThreadSummary
from agent_service.app.memory.repository import (
    MemoryRepository,
    ThreadNotFoundError,
    ThreadVersionConflictError,
)
from agent_service.app.memory.service import RollingSummaryService
from agent_service.app.shared.database import Base


def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def test_memory_revision_summary_versions_and_context_window() -> None:
    factory = session_factory()

    class RecordingSummarizer:
        def __init__(self) -> None:
            self.previous: list[str | None] = []

        async def summarize(self, previous_summary, messages) -> str:
            self.previous.append(previous_summary)
            return " | ".join(
                part for part in [previous_summary, *(message.content for message in messages)] if part
            )

    with factory() as db:
        repository = MemoryRepository(db)
        thread = repository.create_thread(
            tenant_id=1,
            user_id=10,
            agent_key="recruitment",
            agent_version=1,
            title="Summer window",
        )
        revision = 0
        for index in range(1, 9):
            role = MessageRole.USER if index % 2 else MessageRole.ASSISTANT
            _, revision = repository.append_message(
                thread_id=thread.id,
                tenant_id=1,
                user_id=10,
                role=role,
                content=f"message-{index}",
                tool_name=None,
                tool_call_id=None,
                metadata={},
                expected_revision=revision,
            )

        with pytest.raises(ThreadVersionConflictError):
            repository.append_message(
                thread_id=thread.id,
                tenant_id=1,
                user_id=10,
                role=MessageRole.USER,
                content="stale write",
                tool_name=None,
                tool_call_id=None,
                metadata={},
                expected_revision=0,
            )
        with pytest.raises(ThreadNotFoundError):
            repository.get_owned_thread(thread.id, tenant_id=2, user_id=10)

        summarizer = RecordingSummarizer()
        summary = asyncio.run(RollingSummaryService(repository, summarizer).roll_if_needed(
            thread_id=thread.id,
            tenant_id=1,
            user_id=10,
            retain_recent_messages=2,
        ))
        assert summary is not None
        assert summary.version == 1
        assert summary.summarized_through_sequence == 6

        window = MemoryContextBuilder(repository).build(
            thread_id=thread.id,
            tenant_id=1,
            user_id=10,
            max_estimated_tokens=1_000,
        )
        assert window.summary_version == 1
        assert isinstance(window.messages[0], SystemMessage)
        assert [message.content for message in window.messages[1:]] == ["message-7", "message-8"]

        # 极小窗口仍只保留连续的最新消息后缀，不会跳过中间消息后再拼接旧消息。
        tiny = MemoryContextBuilder(repository).build(
            thread_id=thread.id,
            tenant_id=1,
            user_id=10,
            max_estimated_tokens=3,
        )
        assert tiny.dropped_message_count == 1
        assert [message.content for message in tiny.messages] == ["message-8"]

        summaries = list(db.scalars(select(ThreadSummary).where(ThreadSummary.thread_id == thread.id)))
        assert len(summaries) == 1
