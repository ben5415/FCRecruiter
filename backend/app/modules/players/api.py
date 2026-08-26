from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.players.repository import PlayerRepository
from app.modules.players.ratings import position_rating_grade, rating_grade
from app.modules.players.schemas import PlayerDetail, PlayerListItem, PlayerPage
from app.shared.database import get_db_session


router = APIRouter(
    prefix="/players", tags=["players"], dependencies=[Depends(get_current_user)]
)

ATTRIBUTE_GROUPS = {
    "Summary": ["pace", "shooting", "passing", "dribbling", "defending", "physic"],
    "Attacking": ["attacking_crossing", "attacking_finishing", "attacking_heading_accuracy", "attacking_short_passing", "attacking_volleys"],
    "Skill": ["skill_dribbling", "skill_curve", "skill_fk_accuracy", "skill_long_passing", "skill_ball_control"],
    "Movement": ["movement_acceleration", "movement_sprint_speed", "movement_agility", "movement_reactions", "movement_balance"],
    "Power": ["power_shot_power", "power_jumping", "power_stamina", "power_strength", "power_long_shots"],
    "Mentality": ["mentality_aggression", "mentality_interceptions", "mentality_positioning", "mentality_vision", "mentality_penalties", "mentality_composure"],
    "Defending": ["defending_marking_awareness", "defending_standing_tackle", "defending_sliding_tackle"],
    "Goalkeeping": ["goalkeeping_diving", "goalkeeping_handling", "goalkeeping_kicking", "goalkeeping_positioning", "goalkeeping_reflexes", "goalkeeping_speed"],
}
POSITION_RATINGS = ["ls", "st", "rs", "lw", "lf", "cf", "rf", "rw", "lam", "cam", "ram", "lm", "lcm", "cm", "rcm", "rm", "lwb", "ldm", "cdm", "rdm", "rwb", "lb", "lcb", "cb", "rcb", "rb", "gk"]


@router.get("", response_model=PlayerPage)
async def list_players(
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 24,
    search: Annotated[str | None, Query(max_length=100)] = None,
    position: Annotated[str | None, Query(max_length=10)] = None,
) -> PlayerPage:
    result = PlayerRepository(session).list_players(
        page=page,
        page_size=page_size,
        search=search,
        position=position,
        excluded_club_id=current_user.tenant.club_team_id,
    )
    return PlayerPage(
        items=[PlayerListItem.model_validate(player) for player in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        pages=result.pages,
    )


@router.get("/{player_id}", response_model=PlayerDetail)
async def get_player_detail(
    player_id: int,
    session: Annotated[Session, Depends(get_db_session)],
) -> PlayerDetail:
    row = PlayerRepository(session).get_player_detail(player_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    base_fields = {
        field: row[field]
        for field in PlayerDetail.model_fields
        if field not in {"attributes", "position_ratings"}
    }
    return PlayerDetail(
        **base_fields,
        attributes={group: {field: rating_grade(row[field]) for field in fields} for group, fields in ATTRIBUTE_GROUPS.items()},
        position_ratings={position: position_rating_grade(row[position]) for position in POSITION_RATINGS},
    )
