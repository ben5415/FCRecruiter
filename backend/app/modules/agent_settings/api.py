"""将经理操作安全地代理到 Agent Service。"""
from typing import Annotated, Any
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from app.config import get_settings
from app.modules.agent_settings.schemas import AgentDefinitionList, AgentDefinitionView, RegistrationResult
from app.modules.auth.dependencies import AuthContext, require_csrf, require_manager
from app.modules.auth.models import User

router = APIRouter(prefix="/agent-settings", tags=["agent-settings"])
Manager = Annotated[User, Depends(require_manager)]

async def _request(method: str, path: str) -> Any:
    settings = get_settings()
    if not settings.agent_service_token:
        raise HTTPException(status_code=503, detail="Agent service integration is not configured")
    try:
        async with httpx.AsyncClient(timeout=settings.agent_service_timeout_seconds) as client:
            response = await client.request(method, f"{settings.agent_service_url.rstrip('/')}{path}", headers={"X-Agent-Service-Token": settings.agent_service_token})
    except httpx.RequestError as error:
        raise HTTPException(status_code=503, detail="Agent service is unavailable") from error
    if response.is_error:
        try:
            detail = response.json().get("detail", "Agent definition request failed")
        except (ValueError, AttributeError):
            detail = "Agent definition request failed"
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()

@router.get("/versions", response_model=AgentDefinitionList)
async def list_versions(_: Manager) -> AgentDefinitionList:
    return AgentDefinitionList.model_validate(await _request("GET", "/agent-definitions/recruitment"))

@router.post("/register-current", response_model=RegistrationResult, status_code=status.HTTP_201_CREATED)
async def register_current(_: Annotated[AuthContext, Depends(require_csrf)], manager: Manager) -> RegistrationResult:
    return RegistrationResult.model_validate(await _request("POST", "/agent-definitions/recruitment/register-current"))

@router.post("/versions/{version}/enable", response_model=AgentDefinitionView)
async def enable_version(version: int, _: Annotated[AuthContext, Depends(require_csrf)], manager: Manager) -> AgentDefinitionView:
    return AgentDefinitionView.model_validate(await _request("POST", f"/agent-definitions/recruitment/versions/{version}/enable"))

@router.post("/versions/{version}/disable", response_model=AgentDefinitionView)
async def disable_version(version: int, _: Annotated[AuthContext, Depends(require_csrf)], manager: Manager) -> AgentDefinitionView:
    return AgentDefinitionView.model_validate(await _request("POST", f"/agent-definitions/recruitment/versions/{version}/disable"))
