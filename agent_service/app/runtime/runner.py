"""轻量级 Agent Loop。

Runner 的职责不是理解足球业务，而是重复执行下面的通用流程：

1. 把消息和允许的 Tool 交给模型；
2. 如果模型请求 Tool，受控执行并把 ToolMessage 追加到上下文；
3. 如果模型给出最终回答，用指定的 Pydantic Model 校验；
4. 任一步骤超时、超预算或输出非法时，返回同类型的结构化降级结果。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from time import perf_counter
from typing import Any, Generic, TypeVar
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, ValidationError

from agent_service.app.runtime.schemas import (
    AgentLimits,
    AgentRunContext,
    AgentRunResult,
    AgentTraceEvent,
)
from agent_service.app.runtime.model_adapter import AgentModelAdapter
from agent_service.app.runtime.tools import ToolRegistry


# Generic 让同一个 Runner 可以返回 RecruitmentReport 或未来其他 Pydantic 报告。
OutputT = TypeVar("OutputT", bound=BaseModel)
# 降级工厂知道错误和可信上下文，并返回与正常输出相同的 Pydantic 类型。
FallbackFactory = Callable[[str, str, AgentRunContext], OutputT]


class AgentRunner(Generic[OutputT]):
    """协调模型、Tool、预算、验证和降级的通用执行器。"""

    def __init__(
        self,
        *,

        
        model: AgentModelAdapter,
        tools: ToolRegistry,
        output_model: type[OutputT],
        fallback_factory: FallbackFactory[OutputT],
        limits: AgentLimits | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> None:
        # 依赖全部从构造函数注入，便于生产环境换真实模型、测试换 Fake Model。
        self._model = model
        self._tools = tools
        self._output_model = output_model
        self._fallback_factory = fallback_factory
        self._limits = limits or AgentLimits()
        self._allowed_tools = tuple(allowed_tools) if allowed_tools is not None else None

    async def run(
        self,
        *,
        question: str,
        system_prompt: str,
        context: AgentRunContext,
    ) -> AgentRunResult[OutputT]:
        """执行一次完整 Agent Run。"""

        # 每个 Run 从 System + 当前问题开始。未来加入 Thread Memory 时，可以在
        # 这里把摘要和最近消息插入 messages，但下面的循环不需要因此修改。
        messages: list[BaseMessage] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]
        trace: list[AgentTraceEvent] = []
        tool_call_count = 0
        # 这是第一层 Tool Policy：模型只能看到允许的 Tool Schema。
        schemas = self._tools.schemas(self._allowed_tools)

        # 一次“step”表示一次模型调用。模型可以在一个 step 中请求多个 Tool。
        for step in range(1, self._limits.max_steps + 1):
            started = perf_counter()
            try:
                # 模型 Provider 自身可能没有可靠超时，因此 Runtime 再包一层硬超时。
                response = await asyncio.wait_for(
                    self._model.invoke(messages, schemas),
                    timeout=self._limits.model_timeout_seconds,
                )
            except TimeoutError:
                trace.append(_trace(step, "model", "invoke", False, started, "model_timeout"))
                return self._fallback(
                    "model_timeout", "The model did not respond in time", context,
                    step, tool_call_count, trace,
                )
            except Exception:
                trace.append(_trace(step, "model", "invoke", False, started, "model_error"))
                return self._fallback(
                    "model_error", "The model call failed", context,
                    step, tool_call_count, trace,
                )

            messages.append(response)
            trace.append(_trace(step, "model", "invoke", True, started))

            if response.tool_calls:
                # 模型只提出 Tool 调用请求。Runtime 逐个验证和执行，随后进入下一次
                # 模型调用，让模型基于 Tool 结果继续推理。
                for call in response.tool_calls:
                    if tool_call_count >= self._limits.max_tool_calls:
                        return self._fallback(
                            "tool_call_limit_exceeded",
                            "The agent exceeded its tool-call budget",
                            context,
                            step,
                            tool_call_count,
                            trace,
                        )

                    tool_call_count += 1
                    # Tool Call ID 用于把返回的 ToolMessage 与模型原请求对应起来。
                    name = str(call.get("name", ""))
                    call_id = str(call.get("id") or uuid4())
                    tool_started = perf_counter()
                    result = await self._tools.execute(
                        name=name,
                        arguments=call.get("args", {}),
                        tool_call_id=call_id,
                        context=context,
                        timeout_seconds=self._limits.tool_timeout_seconds,
                        allowed_names=self._allowed_tools,
                    )
                    trace.append(
                        _trace(
                            step,
                            "tool",
                            name or "unknown",
                            result.ok,
                            tool_started,
                            result.error_code,
                        )
                    )
                    messages.append(
                        ToolMessage(
                            name=name or None,
                            tool_call_id=call_id,
                            content=result.model_dump_json(),
                        )
                    )
                # 只要本轮出现 Tool Call，就不把 response.content 当最终答案。
                continue

            # 没有 Tool Call 意味着模型认为任务已完成。这里不直接把字符串返回前端，
            # 而是强制用业务指定的 Pydantic Schema 做最终边界校验。
            validation_started = perf_counter()
            try:
                output = self._output_model.model_validate_json(_message_text(response))
            except (ValidationError, ValueError, TypeError):
                trace.append(
                    _trace(
                        step, "validation", "structured_output", False,
                        validation_started, "invalid_structured_output",
                    )
                )
                return self._fallback(
                    "invalid_structured_output",
                    "The model returned an invalid structured report",
                    context,
                    step,
                    tool_call_count,
                    trace,
                )

            trace.append(_trace(step, "validation", "structured_output", True, validation_started))
            return AgentRunResult[OutputT](
                output=output,
                step_count=step,
                tool_call_count=tool_call_count,
                trace=trace,
            )

        # 循环自然结束说明每一步模型都在请求 Tool，始终没有生成最终报告。
        return self._fallback(
            "step_limit_exceeded",
            "The agent did not finish within its step budget",
            context,
            self._limits.max_steps,
            tool_call_count,
            trace,
        )

    def _fallback(
        self,
        code: str,
        message: str,
        context: AgentRunContext,
        step_count: int,
        tool_call_count: int,
        trace: list[AgentTraceEvent],
    ) -> AgentRunResult[OutputT]:
        """把运行异常转换成与正常响应相同类型的安全降级结果。"""

        started = perf_counter()
        fallback = self._fallback_factory(code, message, context)
        output = self._output_model.model_validate(fallback)
        trace.append(_trace(step_count, "fallback", code, True, started, code))
        return AgentRunResult[OutputT](
            output=output,
            degraded=True,
            error_code=code,
            step_count=step_count,
            tool_call_count=tool_call_count,
            trace=trace,
        )


def _message_text(message: AIMessage) -> str:
    """兼容 LangChain 的纯字符串和内容块两种 AIMessage 表示。"""

    if isinstance(message.content, str):
        return message.content
    text_parts = []
    for block in message.content:
        if isinstance(block, str):
            text_parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(str(block.get("text", "")))
    return "".join(text_parts)


def _trace(
    step: int,
    event_type: Any,
    name: str,
    success: bool,
    started: float,
    error_code: str | None = None,
) -> AgentTraceEvent:
    """根据开始时间创建轻量轨迹；暂时只在内存中保存。"""

    details = {"error_code": error_code} if error_code else {}
    return AgentTraceEvent(
        step=step,
        event_type=event_type,
        name=name,
        success=success,
        latency_ms=max(0, round((perf_counter() - started) * 1000)),
        details=details,
    )
