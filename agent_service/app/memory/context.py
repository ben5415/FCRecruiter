"""把持久化 Memory 裁剪为一次模型调用可消费的消息窗口。"""

from dataclasses import dataclass
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from agent_service.app.memory.models import ConversationMessage, MessageRole
from agent_service.app.memory.repository import MemoryRepository


@dataclass(frozen=True)
class ContextWindow:
    messages: tuple[BaseMessage, ...]
    thread_revision: int
    summary_version: int
    dropped_message_count: int
    estimated_tokens: int


class MemoryContextBuilder:
    def __init__(self, repository: MemoryRepository) -> None:
        self._repository = repository

    def build(
        self,
        *,
        thread_id: UUID,
        tenant_id: int,
        user_id: int,
        max_estimated_tokens: int = 2_000,
    ) -> ContextWindow:
        snapshot = self._repository.summary_snapshot(thread_id, tenant_id, user_id)
        selected: list[BaseMessage] = []
        used = 0

        if snapshot.previous_summary:
            summary_message = SystemMessage(
                content=(
                    f"Conversation summary v{snapshot.current_version} "
                    f"(through message {snapshot.summarized_through_sequence}):\n"
                    f"{snapshot.previous_summary}"
                )
            )
            summary_cost = _estimate_tokens(str(summary_message.content))
            if summary_cost <= max_estimated_tokens:
                selected.append(summary_message)
                used += summary_cost

        recent: list[BaseMessage] = []
        # 从最新消息倒序选择，保证预算不足时优先保留最近上下文。
        for message in reversed(snapshot.messages):
            converted = _to_langchain_message(message)
            cost = _estimate_tokens(message.content)
            if used + cost > max_estimated_tokens:
                # 停止而不是跳过中间消息，避免构造出有语义断层的历史后缀。
                break
            recent.append(converted)
            used += cost
        recent.reverse()
        selected.extend(recent)
        return ContextWindow(
            messages=tuple(selected),
            thread_revision=snapshot.revision,
            summary_version=snapshot.current_version,
            dropped_message_count=len(snapshot.messages) - len(recent),
            estimated_tokens=used,
        )


def _estimate_tokens(text: str) -> int:
    # 无 tokenizer 依赖的保守估算；未来可按具体模型替换实现。
    return max(1, (len(text) + 3) // 4)


def _to_langchain_message(message: ConversationMessage) -> BaseMessage:
    if message.role == MessageRole.USER:
        return HumanMessage(content=message.content)
    if message.role == MessageRole.ASSISTANT:
        return AIMessage(content=message.content)
    if message.role == MessageRole.SYSTEM:
        return SystemMessage(content=message.content)
    return ToolMessage(
        content=message.content,
        tool_call_id=message.tool_call_id or f"stored-{message.id}",
        name=message.tool_name,
    )
