import unicodedata

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.modules.players.models import Club, Country, League, Player
from app.modules.players.repository import PlayerRepository
from app.modules.team.repository import TeamRepository
from app.shared.database import Base


def build_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def register_unaccent(dbapi_connection, _connection_record) -> None:
        def unaccent(value: str | None) -> str | None:
            if value is None:
                return None
            normalized = unicodedata.normalize("NFKD", value)
            return "".join(char for char in normalized if not unicodedata.combining(char))

        dbapi_connection.create_function("unaccent", 1, unaccent)

    Base.metadata.create_all(engine)
    session = Session(engine)
    league = League(league_id=1, league_name="Test League")
    club = Club(club_team_id=10, club_name="Test Club", league=league)
    country = Country(nationality_id=100, nationality_name="Test Nation")
    session.add_all(
        [
            Player(
                player_id=1,
                short_name="A. Midfielder",
                player_positions="CM, CDM",
                overall=85,
                club=club,
                country=country,
            ),
            Player(
                player_id=2,
                short_name="B. Forward",
                player_positions="ST",
                overall=80,
                club=club,
                country=country,
            ),
            Player(
                player_id=3,
                short_name="C. Midfielder",
                player_positions="CM",
                overall=75,
                club=club,
                country=country,
            ),
            Player(
                player_id=4,
                short_name="K. Mbappé",
                long_name="Kylian Mbappé Lottin",
                player_positions="ST, LW",
                overall=91,
                club=club,
                country=country,
            ),
            Player(
                player_id=5,
                short_name="Free Agent",
                player_positions="GK",
                overall=60,
                country=country,
            ),
        ]
    )
    session.commit()
    return session


def test_list_players_returns_ranked_page() -> None:
    with build_session() as session:
        result = PlayerRepository(session).list_players(page=1, page_size=2)

        assert result.total == 5
        assert result.pages == 3
        assert [player.player_id for player in result.items] == [4, 1]


def test_list_players_filters_by_name_and_position() -> None:
    with build_session() as session:
        result = PlayerRepository(session).list_players(
            page=1,
            page_size=24,
            search="midfielder",
            position="cm",
        )

        assert result.total == 2
        assert [player.player_id for player in result.items] == [1, 3]


def test_list_players_search_ignores_accents() -> None:
    with build_session() as session:
        result = PlayerRepository(session).list_players(
            page=1,
            page_size=24,
            search="Mbappe",
        )

        assert result.total == 1
        assert result.items[0].short_name == "K. Mbappé"


def test_marketplace_excludes_managed_club_but_keeps_free_agents() -> None:
    with build_session() as session:
        result = PlayerRepository(session).list_players(
            page=1,
            page_size=24,
            excluded_club_id=10,
        )

        assert result.total == 1
        assert result.items[0].short_name == "Free Agent"


def test_team_repository_returns_only_club_squad() -> None:
    with build_session() as session:
        result = TeamRepository(session).get_squad(10)

        assert result is not None
        assert result.club.club_name == "Test Club"
        assert len(result.players) == 4
        assert all(player.club_team_id == 10 for player in result.players)
