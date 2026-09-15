"""滚动摘要策略；摘要生成器通过 Protocol 注入。"""

from typing import Protocol, Sequence
from uuid import UUID

from agent_service.app.memory.models import ConversationMessage, ThreadSummary
from agent_service.app.memory.repository import MemoryRepository


class SummaryGenerator(Protocol):
    async def summarize(
        self,
        previous_summary: str | None,
        messages: Sequence[ConversationMessage],
    ) -> str: ...


class RollingSummaryService:
    def __init__(self, repository: MemoryRepository, generator: SummaryGenerator) -> None:
        self._repository = repository
        self._generator = generator

    async def roll_if_needed(
        self,
        *,
        thread_id: UUID,
        tenant_id: int,
        user_id: int,
        retain_recent_messages: int = 6,
    ) -> ThreadSummary | None:
        snapshot = self._repository.summary_snapshot(thread_id, tenant_id, user_id)
        if len(snapshot.messages) <= retain_recent_messages:
            return None

        messages_to_summarize = snapshot.messages[:-retain_recent_messages]
        content = (await self._generator.summarize(
            snapshot.previous_summary, messages_to_summarize
        )).strip()
        if not content:
            raise ValueError("Summary generator returned empty content")
        return self._repository.save_summary(
            snapshot=snapshot,
            content=content,
            summarized_through_sequence=messages_to_summarize[-1].sequence,
        )
