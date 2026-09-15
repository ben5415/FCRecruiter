"""Memory 持久化与乐观并发控制。"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from agent_service.app.memory.models import (
    ConversationMessage,
    ConversationThread,
    MessageRole,
    ThreadSummary,
)


class ThreadNotFoundError(LookupError):
    pass


class ThreadVersionConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class SummarySnapshot:
    thread_id: UUID
    revision: int
    current_version: int
    summarized_through_sequence: int
    previous_summary: str | None
    messages: tuple[ConversationMessage, ...]


class MemoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_thread(
        self,
        *,
        tenant_id: int,
        user_id: int,
        agent_key: str,
        agent_version: int,
        title: str | None,
    ) -> ConversationThread:
        thread = ConversationThread(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_key=agent_key,
            agent_version=agent_version,
            title=title,
        )
        self._session.add(thread)
        self._session.commit()
        self._session.refresh(thread)
        return thread

    def get_owned_thread(self, thread_id: UUID, tenant_id: int, user_id: int) -> ConversationThread:
        thread = self._session.scalar(
            select(ConversationThread).where(
                ConversationThread.id == thread_id,
                ConversationThread.tenant_id == tenant_id,
                ConversationThread.user_id == user_id,
            )
        )
        if thread is None:
            raise ThreadNotFoundError("Thread not found")
        return thread

    def append_message(
        self,
        *,
        thread_id: UUID,
        tenant_id: int,
        user_id: int,
        role: MessageRole,
        content: str,
        tool_name: str | None,
        tool_call_id: str | None,
        metadata: dict,
        expected_revision: int,
    ) -> tuple[ConversationMessage, int]:
        thread = self.get_owned_thread(thread_id, tenant_id, user_id)
        if thread.revision != expected_revision:
            raise ThreadVersionConflictError(
                f"Expected thread revision {expected_revision}, current revision is {thread.revision}"
            )
        sequence = thread.next_sequence
        result = self._session.execute(
            update(ConversationThread)
            .where(
                ConversationThread.id == thread.id,
                ConversationThread.revision == expected_revision,
            )
            .values(
                next_sequence=ConversationThread.next_sequence + 1,
                revision=ConversationThread.revision + 1,
            )
        )
        if result.rowcount != 1:
            self._session.rollback()
            raise ThreadVersionConflictError("Thread changed while appending a message")
        message = ConversationMessage(
            thread_id=thread.id,
            sequence=sequence,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            message_metadata=metadata,
        )
        self._session.add(message)
        self._session.commit()
        self._session.refresh(message)
        return message, expected_revision + 1

    def summary_snapshot(
        self, thread_id: UUID, tenant_id: int, user_id: int
    ) -> SummarySnapshot:
        thread = self.get_owned_thread(thread_id, tenant_id, user_id)
        summary = self._session.scalar(
            select(ThreadSummary).where(
                ThreadSummary.thread_id == thread.id,
                ThreadSummary.version == thread.current_summary_version,
            )
        ) if thread.current_summary_version else None
        messages = tuple(self._session.scalars(
            select(ConversationMessage)
            .where(
                ConversationMessage.thread_id == thread.id,
                ConversationMessage.sequence > thread.summarized_through_sequence,
            )
            .order_by(ConversationMessage.sequence)
        ))
        return SummarySnapshot(
            thread_id=thread.id,
            revision=thread.revision,
            current_version=thread.current_summary_version,
            summarized_through_sequence=thread.summarized_through_sequence,
            previous_summary=summary.content if summary else None,
            messages=messages,
        )

    def save_summary(
        self,
        *,
        snapshot: SummarySnapshot,
        content: str,
        summarized_through_sequence: int,
    ) -> ThreadSummary:
        new_version = snapshot.current_version + 1
        result = self._session.execute(
            update(ConversationThread)
            .where(
                ConversationThread.id == snapshot.thread_id,
                ConversationThread.revision == snapshot.revision,
            )
            .values(
                current_summary_version=new_version,
                summarized_through_sequence=summarized_through_sequence,
                revision=ConversationThread.revision + 1,
            )
        )
        if result.rowcount != 1:
            self._session.rollback()
            raise ThreadVersionConflictError("Thread changed while its summary was generated")
        summary = ThreadSummary(
            thread_id=snapshot.thread_id,
            version=new_version,
            summarized_through_sequence=summarized_through_sequence,
            content=content,
        )
        self._session.add(summary)
        self._session.commit()
        self._session.refresh(summary)
        return summary
