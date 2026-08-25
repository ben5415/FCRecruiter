from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.modules.players.schemas import ClubSummary, PlayerListItem
from app.modules.team.repository import TeamRepository
from app.modules.team.schemas import SquadResponse
from app.shared.database import get_db_session


router = APIRouter(prefix="/team", tags=["team"])


@router.get("/squad", response_model=SquadResponse)
async def get_squad(
    session: Annotated[Session, Depends(get_db_session)],
) -> SquadResponse:
    result = TeamRepository(session).get_squad(get_settings().managed_club_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Managed club not found",
        )

    return SquadResponse(
        club=ClubSummary.model_validate(result.club),
        players=[PlayerListItem.model_validate(player) for player in result.players],
        total=len(result.players),
    )
