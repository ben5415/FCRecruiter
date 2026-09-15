from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from agent_service.app.api.dependencies import require_service_token
from agent_service.app.recruitment.prompt import RECRUITMENT_AGENT_KEY, RECRUITMENT_SYSTEM_PROMPT
from agent_service.app.recruitment.schemas import RecruitmentReport
from agent_service.app.recruitment.tools import RECRUITMENT_TOOL_NAMES
from agent_service.app.registry.models import AgentDefinitionStatus
from agent_service.app.registry.repository import AgentDefinitionNotFoundError, AgentDefinitionRepository
from agent_service.app.registry.schemas import AgentDefinitionList, AgentDefinitionView, RegistrationResult
from agent_service.app.shared.database import get_agent_db_session


router = APIRouter(
    prefix="/agent-definitions/recruitment", tags=["agent-definition"],
    dependencies=[Depends(require_service_token)],
)
Database = Annotated[Session, Depends(get_agent_db_session)]


@router.get("", response_model=AgentDefinitionList)
async def list_versions(db: Database) -> AgentDefinitionList:
    return AgentDefinitionList(items=AgentDefinitionRepository(db).list_versions(RECRUITMENT_AGENT_KEY))


@router.post("/register-current", response_model=RegistrationResult, status_code=status.HTTP_201_CREATED)
async def register_current(db: Database) -> RegistrationResult:
    definition, created = AgentDefinitionRepository(db).register_current(
        agent_key=RECRUITMENT_AGENT_KEY,
        name="Recruitment Agent",
        description="Evidence-based squad diagnosis and player recruitment analysis.",
        system_prompt=RECRUITMENT_SYSTEM_PROMPT,
        tool_names=list(RECRUITMENT_TOOL_NAMES),
        output_schema=RecruitmentReport.model_json_schema(),
    )
    return RegistrationResult(definition=definition, created=created)


def _change_status(db: Session, version: int, new_status: AgentDefinitionStatus) -> AgentDefinition:
    try:
        return AgentDefinitionRepository(db).set_status(RECRUITMENT_AGENT_KEY, version, new_status)
    except AgentDefinitionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/versions/{version}/enable", response_model=AgentDefinitionView)
async def enable(version: int, db: Database) -> AgentDefinition:
    return _change_status(db, version, AgentDefinitionStatus.ACTIVE)


@router.post("/versions/{version}/disable", response_model=AgentDefinitionView)
async def disable(version: int, db: Database) -> AgentDefinition:
    return _change_status(db, version, AgentDefinitionStatus.DISABLED)

