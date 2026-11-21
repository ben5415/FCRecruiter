from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.auth.dependencies import AuthContext, get_current_user, require_csrf
from app.modules.auth.models import User, UserRole
from app.modules.tactics.models import TeamTactic
from app.modules.tactics.schemas import CurrentTacticResponse, UpdateCurrentTacticRequest
from app.shared.database import get_db_session


router = APIRouter(
    prefix="/tactics", tags=["tactics"], dependencies=[Depends(get_current_user)]
)


def current_tactic(db: Session, tenant_id: int) -> TeamTactic | None:
    return db.scalar(
        select(TeamTactic)
        .options(joinedload(TeamTactic.updated_by))
        .where(TeamTactic.tenant_id == tenant_id)
    )


@router.get("/current", response_model=CurrentTacticResponse)
async def get_current_tactic(
    db: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> CurrentTacticResponse:
    tactic = current_tactic(db, user.tenant_id)
    if tactic is None:
        return CurrentTacticResponse(
            formation=None, playing_style=None, notes=None, updated_by=None, updated_at=None
        )
    return CurrentTacticResponse.model_validate(tactic)


@router.put("/current", response_model=CurrentTacticResponse)
async def update_current_tactic(
    payload: UpdateCurrentTacticRequest,
    _: Annotated[AuthContext, Depends(require_csrf)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CurrentTacticResponse:
    if user.role not in {UserRole.MANAGER, UserRole.COACH}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and coaches can update tactics",
        )

    tactic = current_tactic(db, user.tenant_id)
    if tactic is None:
        tactic = TeamTactic(tenant_id=user.tenant_id)
        db.add(tactic)
    tactic.formation = payload.formation
    tactic.playing_style = payload.playing_style
    tactic.notes = payload.notes.strip() or None if payload.notes is not None else None
    tactic.updated_by = user
    db.commit()
    db.refresh(tactic)
    return CurrentTacticResponse.model_validate(tactic)
