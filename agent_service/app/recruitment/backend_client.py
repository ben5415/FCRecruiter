"""Agent Service 到业务 Backend 的受控 HTTP 客户端。"""

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from agent_service.app.runtime.schemas import AgentRunContext
from agent_service.app.recruitment.tool_schemas import (
    CandidatePlayerInput,
    InjuryQueryInput,
    InjuryToolResult,
    PlayerSearchInput,
    PlayerSearchToolResult,
    SquadToolResult,
    TacticToolResult,
    ToolPlayer,
)


ResponseT = TypeVar("ResponseT", bound=BaseModel)


class BusinessBackendError(RuntimeError):
    """业务 Backend 拒绝请求或返回非法数据。"""


class BusinessBackendClient:
    def __init__(
        self,
        *,
        base_url: str,
        service_token: str,
        timeout_seconds: float = 5.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not service_token:
            raise ValueError("service_token must not be empty")
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    def _headers(self, context: AgentRunContext) -> dict[str, str]:
        # role 不发送给 Backend；Backend 根据 user_id 自己查询真实角色。
        return {
            "X-Agent-Service-Token": self._service_token,
            "X-Tenant-ID": str(context.tenant_id),
            "X-User-ID": str(context.user_id),
        }

    async def _request(
        self,
        method: str,
        path: str,
        response_model: type[ResponseT],
        context: AgentRunContext,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> ResponseT:
        async def send(client: httpx.AsyncClient) -> httpx.Response:
            return await client.request(
                method,
                f"{self._base_url}{path}",
                headers=self._headers(context),
                json=json_body,
                timeout=self._timeout_seconds,
            )

        try:
            if self._http_client is not None:
                response = await send(self._http_client)
            else:
                async with httpx.AsyncClient() as client:
                    response = await send(client)
            response.raise_for_status()
            return response_model.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as error:
            # 上层 ToolRegistry 会把异常转换成不泄露内部细节的 tool_execution_error。
            raise BusinessBackendError("Business Backend request failed") from error

    async def get_squad(self, context: AgentRunContext) -> SquadToolResult:
        return await self._request(
            "GET", "/internal/agent-tools/squad", SquadToolResult, context
        )

    async def get_tactic(self, context: AgentRunContext) -> TacticToolResult:
        return await self._request(
            "GET", "/internal/agent-tools/tactic", TacticToolResult, context
        )

    async def get_injuries(
        self, payload: InjuryQueryInput, context: AgentRunContext
    ) -> InjuryToolResult:
        return await self._request(
            "POST",
            "/internal/agent-tools/injuries",
            InjuryToolResult,
            context,
            json_body=payload.model_dump(mode="json"),
        )

    async def search_players(
        self, payload: PlayerSearchInput, context: AgentRunContext
    ) -> PlayerSearchToolResult:
        return await self._request(
            "POST",
            "/internal/agent-tools/players/search",
            PlayerSearchToolResult,
            context,
            json_body=payload.model_dump(mode="json"),
        )

    async def get_candidate_player(
        self, payload: CandidatePlayerInput, context: AgentRunContext
    ) -> ToolPlayer:
        return await self._request(
            "GET", f"/internal/agent-tools/players/{payload.player_id}", ToolPlayer, context
        )
