"""Agent Runtime 使用的基础数据结构。

这个文件只定义数据，不执行模型或 Tool。把运行限制、可信身份上下文、
执行轨迹和最终结果集中定义，可以避免 Runner、API 和持久化层各自发明一套格式。
"""

from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


# OutputT 表示 Agent 最终输出的 Pydantic 类型。例如足球 Agent 使用
# RecruitmentReport，未来其他 Agent 可以换成自己的 Report，而无需修改 Runner。
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentLimits(BaseModel):
    """一次 Agent Run 的硬性资源边界。

    这些限制由应用配置，而不是由模型决定。它们用于避免模型陷入循环、
    无限制调用 Tool，或者因为外部服务阻塞而长期占用请求。
    """

    # frozen=True 使对象创建后不可修改，防止执行过程中意外放宽预算。
    model_config = ConfigDict(frozen=True)

    max_steps: int = Field(default=3, ge=1, le=20)
    max_tool_calls: int = Field(default=5, ge=0, le=50)
    model_timeout_seconds: float = Field(default=30, gt=0, le=300)
    tool_timeout_seconds: float = Field(default=5, gt=0, le=120)


class AgentRunContext(BaseModel):
    """由业务应用注入的可信执行身份，绝不能来自模型参数。

    未来 Backend 验证用户 Session 后，把 tenant_id、user_id 和 role 通过
    服务间授权传给 Agent Service。Tool 依赖这个 Context 做租户隔离，模型
    只能决定“调用什么 Tool”，不能决定“以哪个租户的身份调用”。
    """

    model_config = ConfigDict(frozen=True)

    run_id: UUID = Field(default_factory=uuid4)
    tenant_id: int
    user_id: int
    role: str


class AgentTraceEvent(BaseModel):
    """一次模型调用、Tool 调用、输出校验或降级操作的轻量轨迹。"""

    step: int
    event_type: Literal["model", "tool", "validation", "fallback"]
    name: str
    success: bool
    latency_ms: int = Field(ge=0)
    details: dict[str, Any] = Field(default_factory=dict)


class AgentRunResult(BaseModel, Generic[OutputT]):
    """Runner 对上层返回的统一结果。

    output 始终是已经通过 Pydantic 校验的结构；即使模型失败，也通过
    fallback_factory 产生同一种结构，所以上层 API 不必处理两套响应格式。
    """

    output: OutputT
    degraded: bool = False
    error_code: str | None = None
    step_count: int = Field(ge=0)
    tool_call_count: int = Field(ge=0)
    trace: list[AgentTraceEvent] = Field(default_factory=list)
