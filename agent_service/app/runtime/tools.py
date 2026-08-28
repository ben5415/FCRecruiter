"""Tool 的注册、Schema 暴露、参数校验和受控执行。

模型只看到 ToolDefinition 生成的 JSON Schema。真正执行时仍要再次经过白名单、
Pydantic 参数校验、超时和异常处理，不能因为模型生成了一个 tool_call 就直接
相信并执行它。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import inspect
import json
import re
from typing import Any, Awaitable, Callable, Sequence

from pydantic import BaseModel, ValidationError

from agent_service.app.runtime.schemas import AgentRunContext
from agent_service.app.runtime.errors import DuplicateToolError, InvalidToolDefinitionError
from agent_service.app.runtime.model_adapter import ToolSchema


# Handler 同时接收已经验证的业务参数和可信的身份上下文。它既可以是普通函数，
# 也可以是 async 函数，例如未来通过 HTTP 调用 Business Backend。
ToolHandler = Callable[[BaseModel, AgentRunContext], Any | Awaitable[Any]]
TOOL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


@dataclass(frozen=True)
class ToolDefinition:
    """一个可注册 Tool 的完整定义。

    input_model 决定模型参数的 JSON Schema，也负责执行前的运行时校验；
    handler 才是最终会执行的函数。
    """

    name: str
    description: str
    input_model: type[BaseModel]
    handler: ToolHandler

    def __post_init__(self) -> None:
        # 限制名称可以减少不同模型 Provider 对函数名格式支持不一致的问题。
        if not TOOL_NAME_PATTERN.fullmatch(self.name):
            raise InvalidToolDefinitionError(
                "Tool names must use lowercase letters, numbers and underscores"
            )
        if not self.description.strip():
            raise InvalidToolDefinitionError("Tool description cannot be empty")

    def model_schema(self) -> ToolSchema:
        """转换为 LangChain/模型能够理解的 Function Calling Schema。"""

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }


class ToolExecutionResult(BaseModel):
    """发送回模型的统一 Tool 结果，成功和失败都使用同一种格式。"""

    tool_name: str
    tool_call_id: str
    ok: bool
    value: Any = None
    error_code: str | None = None
    error_message: str | None = None


class ToolRegistry:
    """进程内 Tool 注册中心和唯一执行入口。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        """注册 Tool；重复名称直接报错，避免后注册的实现静默覆盖旧实现。"""

        if definition.name in self._tools:
            raise DuplicateToolError(f"Tool {definition.name!r} is already registered")
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def schemas(self, allowed_names: Sequence[str] | None = None) -> list[ToolSchema]:
        """只把当前 Agent 获准使用的 Tool Schema 暴露给模型。"""

        if allowed_names is None:
            definitions = self._tools.values()
        else:
            definitions = [self._tools[name] for name in allowed_names if name in self._tools]
        return [definition.model_schema() for definition in definitions]

    async def execute(
        self,
        *,
        name: str,
        arguments: Any,
        tool_call_id: str,
        context: AgentRunContext,
        timeout_seconds: float,
        allowed_names: Sequence[str] | None = None,
    ) -> ToolExecutionResult:
        """在安全边界内执行一次模型请求的 Tool Call。

        校验顺序刻意固定为：执行白名单 → Tool 是否存在 → 参数 Schema → 超时执行。
        即使模型伪造一个没有暴露给它的 Tool Call，第一层检查也会拒绝。
        """

        # “没有告诉模型”不是安全措施，因此执行层必须再次检查白名单。
        if allowed_names is not None and name not in allowed_names:
            return ToolExecutionResult(
                tool_name=name,
                tool_call_id=tool_call_id,
                ok=False,
                error_code="tool_not_allowed",
                error_message="The requested tool is not allowed for this agent",
            )
        definition = self.get(name)
        if definition is None:
            return ToolExecutionResult(
                tool_name=name,
                tool_call_id=tool_call_id,
                ok=False,
                error_code="unknown_tool",
                error_message="The requested tool is not available",
            )

        try:
            # 模型生成的 arguments 属于不可信输入。校验成功后，Handler 拿到的是
            # 对应 input_model 实例，而不是任意 dict。
            validated = definition.input_model.model_validate(arguments)
        except (ValidationError, TypeError) as error:
            return ToolExecutionResult(
                tool_name=name,
                tool_call_id=tool_call_id,
                ok=False,
                error_code="invalid_tool_arguments",
                error_message=str(error),
            )

        async def invoke_handler() -> Any:
            # 同时兼容同步和异步 Tool，Runner 无需知道 Handler 的实现方式。
            result = definition.handler(validated, context)
            if inspect.isawaitable(result):
                result = await result
            return _json_compatible(result)

        try:
            # wait_for 是每个 Tool 自己的时间边界。超时后取消协程，并把受控错误
            # 作为 ToolMessage 交还模型，让模型有机会调整分析或给出降级结论。
            value = await asyncio.wait_for(invoke_handler(), timeout=timeout_seconds)
            return ToolExecutionResult(
                tool_name=name,
                tool_call_id=tool_call_id,
                ok=True,
                value=value,
            )
        except TimeoutError:
            return ToolExecutionResult(
                tool_name=name,
                tool_call_id=tool_call_id,
                ok=False,
                error_code="tool_timeout",
                error_message="Tool execution timed out",
            )
        except Exception:
            # 不把原始异常内容返回模型，避免内部地址、SQL 或敏感数据泄露。
            return ToolExecutionResult(
                tool_name=name,
                tool_call_id=tool_call_id,
                ok=False,
                error_code="tool_execution_error",
                error_message="Tool execution failed",
            )


def _json_compatible(value: Any) -> Any:
    """把 Handler 返回值转换成能够稳定写入 ToolMessage 的 JSON 数据。"""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return str(value)
