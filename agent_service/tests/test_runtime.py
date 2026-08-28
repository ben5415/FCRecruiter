import asyncio
import json
from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from pydantic import BaseModel, Field
import pytest

from agent_service.app.recruitment.schemas import RecruitmentReport, recruitment_fallback
from agent_service.app.runtime.schemas import AgentLimits, AgentRunContext
from agent_service.app.runtime.errors import DuplicateToolError
from agent_service.app.runtime.model_adapter import ToolSchema
from agent_service.app.runtime.runner import AgentRunner
from agent_service.app.runtime.tools import ToolDefinition, ToolRegistry


class SearchInput(BaseModel):
    position: str
    limit: int = Field(default=5, ge=1, le=10)


class SequenceModel:
    def __init__(self, responses: list[AIMessage], delay: float = 0) -> None:
        self.responses = responses
        self.delay = delay
        self.calls: list[tuple[list[BaseMessage], list[ToolSchema]]] = []

    async def invoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[ToolSchema],
    ) -> AIMessage:
        self.calls.append((list(messages), list(tools)))
        if self.delay:
            await asyncio.sleep(self.delay)
        if not self.responses:
            raise RuntimeError("No fake response configured")
        return self.responses.pop(0)


def context() -> AgentRunContext:
    return AgentRunContext(tenant_id=1, user_id=2, role="manager")


def valid_report() -> str:
    return json.dumps({
        "status": "completed",
        "summary": "Right-wing depth should be reviewed.",
        "needs": [],
        "candidates": [],
        "assumptions": [],
        "uncertainty": "medium",
    })


def runner(
    model: SequenceModel,
    registry: ToolRegistry | None = None,
    limits: AgentLimits | None = None,
) -> AgentRunner[RecruitmentReport]:
    return AgentRunner(
        model=model,
        tools=registry or ToolRegistry(),
        output_model=RecruitmentReport,
        fallback_factory=recruitment_fallback,
        limits=limits,
    )


def test_runner_executes_tool_then_validates_structured_report() -> None:
    seen_contexts: list[AgentRunContext] = []

    async def search_players(arguments: BaseModel, run_context: AgentRunContext):
        seen_contexts.append(run_context)
        return {"position": arguments.position, "players": [{"player_id": 10}]}

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="search_players",
        description="Search eligible recruitment candidates.",
        input_model=SearchInput,
        handler=search_players,
    ))
    model = SequenceModel([
        AIMessage(content="", tool_calls=[{
            "name": "search_players",
            "args": {"position": "RW", "limit": 5},
            "id": "call-1",
            "type": "tool_call",
        }]),
        AIMessage(content=valid_report()),
    ])

    result = asyncio.run(runner(model, registry).run(
        question="What should we recruit?",
        system_prompt="Return JSON.",
        context=context(),
    ))

    assert result.degraded is False
    assert result.step_count == 2
    assert result.tool_call_count == 1
    assert seen_contexts[0].tenant_id == 1
    assert isinstance(model.calls[1][0][-1], ToolMessage)
    tool_payload = json.loads(model.calls[1][0][-1].content)
    assert tool_payload["ok"] is True
    assert tool_payload["value"]["players"][0]["player_id"] == 10


def test_invalid_tool_arguments_are_returned_to_model_without_calling_handler() -> None:
    called = False

    def handler(_arguments: BaseModel, _context: AgentRunContext):
        nonlocal called
        called = True

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="search_players",
        description="Search players.",
        input_model=SearchInput,
        handler=handler,
    ))
    model = SequenceModel([
        AIMessage(content="", tool_calls=[{
            "name": "search_players",
            "args": {"position": "RW", "limit": 99},
            "id": "bad-call",
            "type": "tool_call",
        }]),
        AIMessage(content=valid_report()),
    ])

    result = asyncio.run(runner(model, registry).run(
        question="Analyse",
        system_prompt="Return JSON.",
        context=context(),
    ))

    assert result.degraded is False
    assert called is False
    payload = json.loads(model.calls[1][0][-1].content)
    assert payload["error_code"] == "invalid_tool_arguments"


def test_tool_call_budget_returns_structured_fallback() -> None:
    model = SequenceModel([AIMessage(content="", tool_calls=[{
        "name": "anything", "args": {}, "id": "call-1", "type": "tool_call",
    }])])
    limits = AgentLimits(max_tool_calls=0)

    result = asyncio.run(runner(model, limits=limits).run(
        question="Analyse",
        system_prompt="Return JSON.",
        context=context(),
    ))

    assert result.degraded is True
    assert result.error_code == "tool_call_limit_exceeded"
    assert result.output.status == "degraded"


def test_model_timeout_returns_structured_fallback() -> None:
    model = SequenceModel([AIMessage(content=valid_report())], delay=0.05)
    limits = AgentLimits(model_timeout_seconds=0.01)

    result = asyncio.run(runner(model, limits=limits).run(
        question="Analyse",
        system_prompt="Return JSON.",
        context=context(),
    ))

    assert result.degraded is True
    assert result.error_code == "model_timeout"


def test_tool_timeout_is_returned_to_model() -> None:
    async def slow_tool(_arguments: BaseModel, _context: AgentRunContext):
        await asyncio.sleep(0.05)
        return []

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="search_players",
        description="Search players.",
        input_model=SearchInput,
        handler=slow_tool,
    ))
    model = SequenceModel([
        AIMessage(content="", tool_calls=[{
            "name": "search_players",
            "args": {"position": "RW"},
            "id": "slow-call",
            "type": "tool_call",
        }]),
        AIMessage(content=valid_report()),
    ])

    result = asyncio.run(AgentRunner(
        model=model,
        tools=registry,
        output_model=RecruitmentReport,
        fallback_factory=recruitment_fallback,
        limits=AgentLimits(tool_timeout_seconds=0.01),
    ).run(
        question="Analyse",
        system_prompt="Return JSON.",
        context=context(),
    ))

    assert result.degraded is False
    payload = json.loads(model.calls[1][0][-1].content)
    assert payload["error_code"] == "tool_timeout"


def test_execution_layer_rejects_tool_outside_agent_allowlist() -> None:
    called = False

    def restricted_tool(_arguments: BaseModel, _context: AgentRunContext):
        nonlocal called
        called = True

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="restricted_tool",
        description="A registered tool not granted to this agent.",
        input_model=SearchInput,
        handler=restricted_tool,
    ))
    model = SequenceModel([
        AIMessage(content="", tool_calls=[{
            "name": "restricted_tool",
            "args": {"position": "RW"},
            "id": "restricted-call",
            "type": "tool_call",
        }]),
        AIMessage(content=valid_report()),
    ])

    result = asyncio.run(AgentRunner(
        model=model,
        tools=registry,
        output_model=RecruitmentReport,
        fallback_factory=recruitment_fallback,
        allowed_tools=[],
    ).run(
        question="Analyse",
        system_prompt="Return JSON.",
        context=context(),
    ))

    assert result.degraded is False
    assert called is False
    payload = json.loads(model.calls[1][0][-1].content)
    assert payload["error_code"] == "tool_not_allowed"


def test_invalid_output_returns_structured_fallback() -> None:
    model = SequenceModel([AIMessage(content="not-json")])

    result = asyncio.run(runner(model).run(
        question="Analyse",
        system_prompt="Return JSON.",
        context=context(),
    ))

    assert result.degraded is True
    assert result.error_code == "invalid_structured_output"
    assert result.output.uncertainty == "high"


def test_step_limit_stops_repeated_tool_requests() -> None:
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="search_players",
        description="Search players.",
        input_model=SearchInput,
        handler=lambda arguments, run_context: [],
    ))
    model = SequenceModel([AIMessage(content="", tool_calls=[{
        "name": "search_players",
        "args": {"position": "RW"},
        "id": "call-1",
        "type": "tool_call",
    }])])

    result = asyncio.run(runner(
        model,
        registry,
        AgentLimits(max_steps=1, max_tool_calls=2),
    ).run(
        question="Analyse",
        system_prompt="Return JSON.",
        context=context(),
    ))

    assert result.degraded is True
    assert result.error_code == "step_limit_exceeded"


def test_registry_rejects_duplicate_tools() -> None:
    definition = ToolDefinition(
        name="search_players",
        description="Search players.",
        input_model=SearchInput,
        handler=lambda arguments, run_context: [],
    )
    registry = ToolRegistry()
    registry.register(definition)

    with pytest.raises(DuplicateToolError):
        registry.register(definition)
