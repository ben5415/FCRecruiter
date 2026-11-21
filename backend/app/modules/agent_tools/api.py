"""供 Agent Service 调用的只读、租户隔离业务 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.modules.agent_tools.dependencies import (
    AgentServicePrincipal,
    require_agent_service_principal,
)
from app.modules.agent_tools.schemas import (
    AgentPlayer,
    AgentSquadResponse,
    AgentTacticResponse,
    InjuryEvent,
    InjuryListResponse,
    InjuryQuery,
    PlayerSearchRequest,
    PlayerSearchResponse,
)
from app.modules.events.models import TeamEvent, TeamEventType
from app.modules.players.models import Player
from app.modules.players.ratings import rating_grade
from app.modules.tactics.models import TeamTactic
from app.shared.database import get_db_session


router = APIRouter(prefix="/internal/agent-tools", tags=["internal-agent-tools"])
Principal = Annotated[AgentServicePrincipal, Depends(require_agent_service_principal)]
Database = Annotated[Session, Depends(get_db_session)]


def _agent_player(player: Player) -> AgentPlayer:
    return AgentPlayer(
        player_id=player.player_id,
        name=player.long_name or player.short_name,
        positions=player.player_positions,
        overall=rating_grade(player.overall),
        potential=rating_grade(player.potential),
        age=player.age,
        value_eur=player.value_eur,
        wage_eur=player.wage_eur,
        preferred_foot=player.preferred_foot,
        club_name=player.club.club_name if player.club else None,
        nationality_name=player.country.nationality_name if player.country else None,
    )


@router.get("/squad", response_model=AgentSquadResponse)
async def agent_squad(principal: Principal, db: Database) -> AgentSquadResponse:
    club_id = principal.user.tenant.club_team_id
    players = list(db.scalars(
        select(Player)
        .options(joinedload(Player.club), joinedload(Player.country))
        .where(Player.club_team_id == club_id)
        .order_by(Player.overall.desc().nulls_last(), Player.player_id)
    ).unique())
    return AgentSquadResponse(
        club_name=principal.user.tenant.club.club_name,
        players=[_agent_player(player) for player in players],
        total=len(players),
    )


@router.get("/tactic", response_model=AgentTacticResponse)
async def agent_tactic(principal: Principal, db: Database) -> AgentTacticResponse:
    tactic = db.scalar(select(TeamTactic).where(TeamTactic.tenant_id == principal.tenant_id))
    if tactic is None:
        return AgentTacticResponse(
            formation=None, playing_style=None, notes=None, updated_at=None
        )
    return AgentTacticResponse(
        formation=tactic.formation,
        playing_style=tactic.playing_style,
        notes=tactic.notes,
        updated_at=tactic.updated_at,
    )


@router.post("/injuries", response_model=InjuryListResponse)
async def agent_injuries(
    payload: InjuryQuery,
    principal: Principal,
    db: Database,
) -> InjuryListResponse:
    filters = [
        TeamEvent.tenant_id == principal.tenant_id,
        TeamEvent.event_type == TeamEventType.MEDICAL,
    ]
    if payload.from_date is not None:
        filters.append(TeamEvent.injury_date >= payload.from_date)
    if payload.to_date is not None:
        filters.append(TeamEvent.injury_date <= payload.to_date)
    total = db.scalar(select(func.count()).select_from(TeamEvent).where(*filters)) or 0
    events = list(db.scalars(
        select(TeamEvent)
        .options(joinedload(TeamEvent.player))
        .where(*filters)
        .order_by(TeamEvent.injury_date.desc().nulls_last(), TeamEvent.id.desc())
        .limit(payload.limit)
    ).unique())
    return InjuryListResponse(
        items=[
            InjuryEvent(
                event_id=event.id,
                player_id=event.player_id,
                player_name=event.player.short_name if event.player else None,
                injury_date=event.injury_date,
                description=event.description,
                recovery_days=event.recovery_days,
                expected_return_date=event.expected_return_date,
            )
            for event in events
        ],
        total=total,
    )


@router.post("/players/search", response_model=PlayerSearchResponse)
async def agent_player_search(
    payload: PlayerSearchRequest,
    principal: Principal,
    db: Database,
) -> PlayerSearchResponse:
    """使用固定 SQLAlchemy 条件筛选候选人；模型不能提供 SQL 或任意字段名。"""

    filters = [
        or_(
            Player.club_team_id.is_(None),
            Player.club_team_id != principal.user.tenant.club_team_id,
        )
    ]
    if payload.search:
        pattern = f"%{payload.search}%"
        filters.append(
            or_(
                func.unaccent(Player.short_name).ilike(func.unaccent(pattern)),
                func.unaccent(Player.long_name).ilike(func.unaccent(pattern)),
            )
        )
    if payload.positions:
        filters.append(or_(*[
            Player.player_positions.ilike(f"%{position}%") for position in payload.positions
        ]))
    if payload.min_age is not None:
        filters.append(Player.age >= payload.min_age)
    if payload.max_age is not None:
        filters.append(Player.age <= payload.max_age)
    if payload.max_value_eur is not None:
        filters.append(Player.value_eur <= payload.max_value_eur)
    if payload.max_wage_eur is not None:
        filters.append(Player.wage_eur <= payload.max_wage_eur)
    if payload.preferred_foot is not None:
        filters.append(Player.preferred_foot == payload.preferred_foot)
    if payload.minimum_overall is not None:
        thresholds = {"D": 0, "C": 50, "B": 65, "A": 75, "A+": 85}
        filters.append(Player.overall >= thresholds[payload.minimum_overall])

    total = db.scalar(select(func.count()).select_from(Player).where(*filters)) or 0
    players = list(db.scalars(
        select(Player)
        .options(joinedload(Player.club), joinedload(Player.country))
        .where(*filters)
        .order_by(Player.overall.desc().nulls_last(), Player.potential.desc().nulls_last())
        .limit(payload.limit)
    ).unique())
    return PlayerSearchResponse(
        items=[_agent_player(player) for player in players],
        total_matched=total,
        returned=len(players),
    )


@router.get("/players/{player_id}", response_model=AgentPlayer)
async def agent_candidate_player(
    player_id: int,
    principal: Principal,
    db: Database,
) -> AgentPlayer:
    player = db.scalar(
        select(Player)
        .options(joinedload(Player.club), joinedload(Player.country))
        .where(
            Player.player_id == player_id,
            or_(
                Player.club_team_id.is_(None),
                Player.club_team_id != principal.user.tenant.club_team_id,
            ),
        )
    )
    if player is None:
        raise HTTPException(status_code=404, detail="Candidate player not found")
    return _agent_player(player)
