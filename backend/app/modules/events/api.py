from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.modules.auth.dependencies import AuthContext, get_current_user, require_csrf, require_manager
from app.modules.auth.models import User
from app.modules.events.models import TeamEvent, TeamEventType
from app.modules.events.schemas import (
    CreateTeamEventRequest,
    TeamEventListResponse,
    TeamEventResponse,
    UpdateTeamEventRequest,
)
from app.modules.events.service import require_write_permission, validate_event_fields
from app.modules.players.models import Player
from app.modules.auth.schemas import MessageResponse
from app.shared.database import get_db_session


router = APIRouter(
    prefix="/events", tags=["events"], dependencies=[Depends(get_current_user)]
)


def event_for_tenant(db: Session, event_id: int, tenant_id: int) -> TeamEvent:
    event = db.scalar(
        select(TeamEvent)
        .options(joinedload(TeamEvent.player), joinedload(TeamEvent.created_by))
        .where(TeamEvent.id == event_id, TeamEvent.tenant_id == tenant_id)
    )
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def ensure_squad_player(db: Session, player_id: int | None, user: User) -> None:
    if player_id is None:
        return
    player = db.scalar(
        select(Player).where(
            Player.player_id == player_id,
            Player.club_team_id == user.tenant.club_team_id,
        )
    )
    if player is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player does not belong to this tenant's club",
        )


@router.get("", response_model=TeamEventListResponse)
async def list_events(
    db: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    event_type: Annotated[TeamEventType | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TeamEventListResponse:
    filters = [TeamEvent.tenant_id == user.tenant_id]
    if event_type is not None:
        filters.append(TeamEvent.event_type == event_type)
    total = db.scalar(select(func.count()).select_from(TeamEvent).where(*filters)) or 0
    events = db.scalars(
        select(TeamEvent)
        .options(joinedload(TeamEvent.player), joinedload(TeamEvent.created_by))
        .where(*filters)
        .order_by(TeamEvent.created_at.desc(), TeamEvent.id.desc())
        .limit(limit)
        .offset(offset)
    ).unique().all()
    return TeamEventListResponse(
        items=[TeamEventResponse.model_validate(event) for event in events], total=total
    )


@router.post("", response_model=TeamEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: CreateTeamEventRequest,
    _: Annotated[AuthContext, Depends(require_csrf)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> TeamEventResponse:
    require_write_permission(user, payload.event_type)
    values = payload.model_dump(exclude={"event_type"})
    validate_event_fields(payload.event_type, values)
    ensure_squad_player(db, payload.player_id, user)
    event = TeamEvent(
        tenant_id=user.tenant_id,
        created_by_user_id=user.id,
        event_type=payload.event_type,
        **values,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return TeamEventResponse.model_validate(event)


@router.patch("/{event_id}", response_model=TeamEventResponse)
async def update_event(
    event_id: int,
    payload: UpdateTeamEventRequest,
    _: Annotated[AuthContext, Depends(require_csrf)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> TeamEventResponse:
    event = event_for_tenant(db, event_id, user.tenant_id)
    require_write_permission(user, event.event_type)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes supplied")
    values = {
        "player_id": event.player_id,
        "injury_date": event.injury_date,
        "event_date": event.event_date,
        "description": event.description,
        "recovery_days": event.recovery_days,
        "training_project": event.training_project,
        "training_effect": event.training_effect,
        **changes,
    }
    validate_event_fields(event.event_type, values)
    ensure_squad_player(db, values.get("player_id"), user)
    for field, value in changes.items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return TeamEventResponse.model_validate(event)


@router.delete("/{event_id}", response_model=MessageResponse)
async def delete_event(
    event_id: int,
    _: Annotated[AuthContext, Depends(require_csrf)],
    manager: Annotated[User, Depends(require_manager)],
    db: Annotated[Session, Depends(get_db_session)],
) -> MessageResponse:
    event = event_for_tenant(db, event_id, manager.tenant_id)
    db.delete(event)
    db.commit()
    return MessageResponse(message="Event deleted")
