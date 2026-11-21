"""登录用户使用的招募 Agent 代理，浏览器不接触服务密钥。"""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.modules.auth.dependencies import AuthContext, require_csrf
from app.modules.recruitment.schemas import RecruitmentAnalysisRequest, RecruitmentAnalysisResponse


router = APIRouter(prefix="/recruitment", tags=["recruitment-agent"])


@router.post("/analyse", response_model=RecruitmentAnalysisResponse)
async def analyse_recruitment(
    payload: RecruitmentAnalysisRequest,
    context: Annotated[AuthContext, Depends(require_csrf)],
) -> RecruitmentAnalysisResponse:
    settings = get_settings()
    if not settings.agent_service_token:
        raise HTTPException(status_code=503, detail="Agent service integration is not configured")
    headers = {
        "X-Agent-Service-Token": settings.agent_service_token,
        "X-Tenant-ID": str(context.user.tenant_id),
        "X-User-ID": str(context.user.id),
    }
    try:
        async with httpx.AsyncClient(timeout=settings.agent_service_timeout_seconds) as client:
            response = await client.post(
                f"{settings.agent_service_url.rstrip('/')}/recruitment/analyse",
                headers=headers,
                json=payload.model_dump(mode="json"),
            )
    except httpx.RequestError as error:
        raise HTTPException(status_code=503, detail="Recruitment Agent is unavailable") from error
    if response.is_error:
        detail = "Recruitment analysis failed"
        try:
            remote = response.json().get("detail")
            if isinstance(remote, str):
                detail = remote
        except (ValueError, AttributeError):
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)
    return RecruitmentAnalysisResponse.model_validate(response.json())
