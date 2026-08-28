"""模型适配层。

Runner 只依赖 AgentModelAdapter 协议，不直接依赖 DeepSeek、OpenAI 或其他
Provider。生产环境可以注入 LangChainModelAdapter，单元测试则注入 Fake Model，
从而避免测试消耗 Token，也让更换模型不影响 Agent Loop。

Agent和框架本身解耦。
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage

from agent_service.app.runtime.errors import ModelResponseError


# 这是发送给 LangChain bind_tools() 的标准函数调用描述。
ToolSchema = dict[str, Any]


class AgentModelAdapter(Protocol):
    """Runner 需要的最小模型能力：接收消息和 Tool Schema，返回 AIMessage。"""

    async def invoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[ToolSchema],
    ) -> AIMessage: ...


class LangChainModelAdapter:
    """把支持 ``bind_tools`` 的 LangChain ChatModel 适配到 Runtime 协议。"""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def invoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[ToolSchema],
    ) -> AIMessage:
        # bind_tools 只是在本次模型调用中声明“有哪些函数可用”。模型不会在这里
        # 直接执行 Python 函数；它只会在 AIMessage.tool_calls 中提出调用请求。
        bound_model = self._model.bind_tools(list(tools))
        response = await bound_model.ainvoke(list(messages))
        # Runner 后续依赖 AIMessage.tool_calls，因此在边界处尽早拒绝异常类型。
        if not isinstance(response, AIMessage):
            raise ModelResponseError("Chat model did not return an AIMessage")
        return response
