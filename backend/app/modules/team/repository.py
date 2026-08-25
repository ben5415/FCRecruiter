from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.players.models import Club, Player


@dataclass(frozen=True)
class SquadResult:
    club: Club
    players: list[Player]


class TeamRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_squad(self, club_id: int) -> SquadResult | None:
        club = self.session.get(Club, club_id)
        if club is None:
            return None

        statement = (
            select(Player)
            .options(joinedload(Player.club), joinedload(Player.country))
            .where(Player.club_team_id == club_id)
            .order_by(Player.overall.desc().nulls_last(), Player.player_id)
        )
        players = list(self.session.scalars(statement).unique().all())
        return SquadResult(club=club, players=players)
