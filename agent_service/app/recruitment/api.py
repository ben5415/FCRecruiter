"""供业务 Backend 调用的循证招募分析入口。"""

from typing import Annotated
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from agent_service.app.api.dependencies import CallerIdentity, require_caller_identity
from agent_service.app.recruitment.factory import build_recruitment_runner
from agent_service.app.config import get_agent_settings
from agent_service.app.observability.repository import ObservabilityRepository
from agent_service.app.recruitment.prompt import (
    RECRUITMENT_AGENT_KEY,
)
from agent_service.app.recruitment.schemas import RecruitmentReport
from agent_service.app.recruitment.tools import RECRUITMENT_TOOL_NAMES
from agent_service.app.runtime.schemas import AgentRunContext, AgentRunResult
from agent_service.app.shared.database import get_agent_db_session
from agent_service.app.registry.repository import ActiveAgentDefinitionNotFoundError, AgentDefinitionRepository


class RecruitmentAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=3, max_length=4_000)
    player_id: int | None = Field(default=None, gt=0)


router = APIRouter(prefix="/recruitment", tags=["recruitment-agent"])
Database = Annotated[Session, Depends(get_agent_db_session)]
Identity = Annotated[CallerIdentity, Depends(require_caller_identity)]


@router.post("/analyse", response_model=AgentRunResult[RecruitmentReport])
async def analyse_recruitment(
    payload: RecruitmentAnalysisRequest,
    identity: Identity,
    db: Database,
) -> AgentRunResult[RecruitmentReport]:
    try:
        definition = AgentDefinitionRepository(db).discover_active(RECRUITMENT_AGENT_KEY)
    except ActiveAgentDefinitionNotFoundError as error:
        raise HTTPException(status_code=503, detail="Recruitment Agent has no active version") from error
    try:
        runner = build_recruitment_runner(allowed_tools=definition.tool_names)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Recruitment Agent is not configured") from error
    context = AgentRunContext(
        tenant_id=identity.tenant_id,
        user_id=identity.user_id,
        # Backend Tool API 会重新查询真实角色；Agent Service 不伪造角色授权。
        role="backend_authenticated",
    )
    started = perf_counter()
    question = payload.question
    if payload.player_id is not None:
        question = (
            f"{question}\n\nThe user selected exact player_id={payload.player_id}. "
            f"You must call get_candidate_player with player_id={payload.player_id}, then compare "
            "the candidate with the current squad and current tactic."
        )
    result = await runner.run(
        question=question,
        system_prompt=definition.system_prompt,
        context=context,
    )
    ObservabilityRepository(db).save_run(
        context=context,
        agent_key=RECRUITMENT_AGENT_KEY,
        agent_version=definition.version,
        model_name=get_agent_settings().deepseek_model,
        question=question,
        result=result,
        latency_ms=max(0, round((perf_counter() - started) * 1000)),
    )
    return result
