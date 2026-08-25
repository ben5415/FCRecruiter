from dataclasses import dataclass
from math import ceil

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, joinedload

from app.modules.players.models import Player


@dataclass(frozen=True)
class PlayerPageResult:
    items: list[Player]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        return ceil(self.total / self.page_size) if self.total else 0


class PlayerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_players(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        position: str | None = None,
        excluded_club_id: int | None = None,
    ) -> PlayerPageResult:
        filters = []
        normalized_search = search.strip() if search else None
        normalized_position = position.strip().upper() if position else None

        if normalized_search:
            pattern = f"%{normalized_search}%"
            filters.append(
                func.unaccent(Player.short_name).ilike(func.unaccent(pattern))
                | func.unaccent(Player.long_name).ilike(func.unaccent(pattern))
            )
        if normalized_position:
            filters.append(Player.player_positions.ilike(f"%{normalized_position}%"))
        if excluded_club_id is not None:
            filters.append(
                or_(
                    Player.club_team_id.is_(None),
                    Player.club_team_id != excluded_club_id,
                )
            )

        total = self.session.scalar(
            select(func.count()).select_from(Player).where(*filters)
        ) or 0
        statement = (
            select(Player)
            .options(joinedload(Player.club), joinedload(Player.country))
            .where(*filters)
            .order_by(Player.overall.desc().nulls_last(), Player.player_id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        players = list(self.session.scalars(statement).unique().all())

        return PlayerPageResult(players, page, page_size, total)

    def get_player_detail(self, player_id: int):
        return self.session.execute(
            text(
                """
                SELECT p.*, c.club_name, l.league_name, n.nationality_name
                FROM players AS p
                LEFT JOIN clubs AS c ON c.club_team_id = p.club_team_id
                LEFT JOIN leagues AS l ON l.league_id = c.league_id
                LEFT JOIN countries AS n ON n.nationality_id = p.nationality_id
                WHERE p.player_id = :player_id
                """
            ),
            {"player_id": player_id},
        ).mappings().first()
