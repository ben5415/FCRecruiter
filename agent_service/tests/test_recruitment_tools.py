import asyncio
import json

import httpx

from agent_service.app.recruitment.backend_client import BusinessBackendClient
from agent_service.app.recruitment.tools import (
    RECRUITMENT_TOOL_NAMES,
    build_recruitment_tool_registry,
)
from agent_service.app.runtime.schemas import AgentRunContext


def test_recruitment_tools_use_typed_arguments_and_trusted_identity_headers() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/players/7"):
            return httpx.Response(200, json={
                "player_id": 7, "name": "Candidate", "positions": "RW",
                "overall": "A", "potential": "A+", "age": 21,
                "value_eur": 20_000_000, "wage_eur": 50_000,
                "preferred_foot": "Left", "club_name": "Other FC",
                "nationality_name": "England",
            })
        if request.url.path.endswith("/players/search"):
            return httpx.Response(200, json={
                "items": [{
                    "player_id": 7, "name": "Candidate", "positions": "RW",
                    "overall": "A", "potential": "A+", "age": 21,
                    "value_eur": 20_000_000, "wage_eur": 50_000,
                    "preferred_foot": "Left", "club_name": "Other FC",
                    "nationality_name": "England",
                }],
                "total_matched": 1,
                "returned": 1,
            })
        raise AssertionError(f"Unexpected request: {request.url}")

    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://backend"
        ) as http_client:
            client = BusinessBackendClient(
                base_url="http://backend/api",
                service_token="service-secret",
                http_client=http_client,
            )
            registry = build_recruitment_tool_registry(client)
            assert [schema["function"]["name"] for schema in registry.schemas()] == list(
                RECRUITMENT_TOOL_NAMES
            )
            context = AgentRunContext(tenant_id=15, user_id=29, role="manager")
            result = await registry.execute(
                name="search_players",
                arguments={"positions": ["RW"], "max_age": 23, "limit": 5},
                tool_call_id="call-1",
                context=context,
                timeout_seconds=1,
                allowed_names=RECRUITMENT_TOOL_NAMES,
            )
            assert result.ok is True
            assert result.value["items"][0]["overall"] == "A"
            assert requests[0].headers["X-Tenant-ID"] == "15"
            assert requests[0].headers["X-User-ID"] == "29"
            assert "role" not in requests[0].headers
            assert json.loads(requests[0].content)["positions"] == ["RW"]

            candidate = await registry.execute(
                name="get_candidate_player",
                arguments={"player_id": 7},
                tool_call_id="candidate-call",
                context=context,
                timeout_seconds=1,
                allowed_names=RECRUITMENT_TOOL_NAMES,
            )
            assert candidate.ok is True
            assert candidate.value["evidence_source_id"] == "player:7"

            rejected = await registry.execute(
                name="search_players",
                arguments={"positions": ["RW"], "sql": "SELECT * FROM users"},
                tool_call_id="call-2",
                context=context,
                timeout_seconds=1,
                allowed_names=RECRUITMENT_TOOL_NAMES,
            )
            assert rejected.ok is False
            assert rejected.error_code == "invalid_tool_arguments"
            assert len(requests) == 2

    asyncio.run(scenario())
