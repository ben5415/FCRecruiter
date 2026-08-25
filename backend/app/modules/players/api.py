from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.modules.players.repository import PlayerRepository
from app.modules.players.schemas import PlayerListItem, PlayerPage
from app.shared.database import get_db_session


router = APIRouter(prefix="/players", tags=["players"])


@router.get("", response_model=PlayerPage)
async def list_players(
    session: Annotated[Session, Depends(get_db_session)],
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
        excluded_club_id=get_settings().managed_club_id,
    )
    return PlayerPage(
        items=[PlayerListItem.model_validate(player) for player in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        pages=result.pages,
    )
