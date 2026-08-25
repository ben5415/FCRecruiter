from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.players.repository import PlayerRepository
from app.modules.players.schemas import PlayerListItem, PlayerPage
from app.shared.database import get_db_session


router = APIRouter(
    prefix="/players", tags=["players"], dependencies=[Depends(get_current_user)]
)


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
        excluded_club_id=current_user.managed_club_team_id,
    )
    return PlayerPage(
        items=[PlayerListItem.model_validate(player) for player in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        pages=result.pages,
    )
