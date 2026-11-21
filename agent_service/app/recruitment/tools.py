"""足球招募场景的类型化 Tool 定义与注册。"""

from agent_service.app.config import get_agent_settings
from agent_service.app.knowledge import build_knowledge_service_from_settings
from agent_service.app.knowledge.service import KnowledgeService
from agent_service.app.recruitment.backend_client import BusinessBackendClient
from agent_service.app.recruitment.tool_schemas import (
    CandidatePlayerInput,
    EmptyToolInput,
    InjuryQueryInput,
    KnowledgeSearchInput,
    PlayerSearchInput,
)
from agent_service.app.runtime.schemas import AgentRunContext
from agent_service.app.runtime.tools import ToolDefinition, ToolRegistry


RECRUITMENT_TOOL_NAMES = (
    "get_squad",
    "get_current_tactic",
    "get_injury_events",
    "search_players",
    "get_candidate_player",
    "search_football_knowledge",
)


def build_recruitment_tools_from_settings() -> ToolRegistry:
    """使用环境配置创建生产装配；测试仍可直接注入 Fake/Mock Client。"""

    settings = get_agent_settings()
    if not settings.agent_service_token:
        raise RuntimeError("AGENT_SERVICE_TOKEN is required for recruitment tools")
    client = BusinessBackendClient(
        base_url=settings.business_backend_url,
        service_token=settings.agent_service_token,
        timeout_seconds=settings.business_backend_timeout_seconds,
    )
    return build_recruitment_tool_registry(
        client,
        knowledge_service=build_knowledge_service_from_settings(),
    )


def build_recruitment_tool_registry(
    client: BusinessBackendClient,
    knowledge_service: KnowledgeService | None = None,
) -> ToolRegistry:
    """创建招募 Agent 的 Tool Registry；每个 Handler 只调用 Backend API。"""

    registry = ToolRegistry()

    async def get_squad(
        _arguments: EmptyToolInput, context: AgentRunContext
    ):
        return await client.get_squad(context)

    async def get_current_tactic(
        _arguments: EmptyToolInput, context: AgentRunContext
    ):
        return await client.get_tactic(context)

    async def get_injury_events(
        arguments: InjuryQueryInput, context: AgentRunContext
    ):
        return await client.get_injuries(arguments, context)

    async def search_players(
        arguments: PlayerSearchInput, context: AgentRunContext
    ):
        return await client.search_players(arguments, context)

    async def get_candidate_player(
        arguments: CandidatePlayerInput, context: AgentRunContext
    ):
        return await client.get_candidate_player(arguments, context)

    async def search_football_knowledge(
        arguments: KnowledgeSearchInput, context: AgentRunContext
    ):
        if knowledge_service is None:
            raise RuntimeError("Knowledge retrieval is not configured")
        return await knowledge_service.search(
            query=arguments.query,
            tenant_id=context.tenant_id,
            limit=arguments.limit,
            min_similarity=arguments.min_similarity,
        )

    definitions = (
        ToolDefinition(
            name="get_squad",
            description="Read the current tenant club's first-team squad.",
            input_model=EmptyToolInput,
            handler=get_squad,
        ),
        ToolDefinition(
            name="get_current_tactic",
            description="Read the current tenant club's formation, playing style and notes.",
            input_model=EmptyToolInput,
            handler=get_current_tactic,
        ),
        ToolDefinition(
            name="get_injury_events",
            description="Read tenant-scoped medical injury events within an optional date range.",
            input_model=InjuryQueryInput,
            handler=get_injury_events,
        ),
        ToolDefinition(
            name="search_players",
            description=(
                "Deterministically filter external recruitment candidates by name, positions, "
                "age, budget, preferred foot and minimum public rating grade."
            ),
            input_model=PlayerSearchInput,
            handler=search_players,
        ),
        ToolDefinition(
            name="get_candidate_player",
            description=(
                "Read one external recruitment candidate by exact player_id. Use this before "
                "assessing a player selected by the user."
            ),
            input_model=CandidatePlayerInput,
            handler=get_candidate_player,
        ),
    )
    for definition in definitions:
        registry.register(definition)
    registry.register(ToolDefinition(
        name="search_football_knowledge",
        description=(
            "Retrieve relevant football knowledge passages. Use returned "
            "evidence_source_id values unchanged in report Evidence."
        ),
        input_model=KnowledgeSearchInput,
        handler=search_football_knowledge,
    ))
    return registry
