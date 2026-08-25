from pydantic import BaseModel, Field

from app.modules.players.schemas import ClubSummary, PlayerListItem


class SquadResponse(BaseModel):
    club: ClubSummary
    players: list[PlayerListItem]
    total: int = Field(ge=0)
