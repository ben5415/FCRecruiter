import asyncio
from datetime import date

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.main import create_app
from app.modules.auth.models import Tenant, User, UserRole
from app.modules.auth.security import hash_password
from app.modules.events.models import TeamEvent, TeamEventType
from app.modules.players.models import Club, Country, Player
from app.modules.tactics.models import Formation, PlayingStyle, TeamTactic
from app.shared.database import Base, get_db_session


def test_agent_tool_api_authentication_tenant_isolation_and_data_boundaries(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_SERVICE_TOKEN", "test-service-secret")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        db.add_all([
            Club(club_team_id=1, club_name="Arsenal"),
            Club(club_team_id=2, club_name="Chelsea"),
            Club(club_team_id=3, club_name="Candidate FC"),
            Country(nationality_id=10, nationality_name="England"),
            Tenant(id=1, name="Arsenal", slug="arsenal", club_team_id=1),
            Tenant(id=2, name="Chelsea", slug="chelsea", club_team_id=2),
            Player(
                player_id=101, short_name="Arsenal Player", player_positions="CM",
                overall=80, potential=83, age=25, club_team_id=1, nationality_id=10,
            ),
            Player(
                player_id=102, short_name="Chelsea Player", player_positions="ST",
                overall=90, potential=91, age=27, club_team_id=2, nationality_id=10,
            ),
            Player(
                player_id=103, short_name="Young Winger", player_positions="RW, LW",
                overall=78, potential=88, age=21, value_eur=25_000_000,
                preferred_foot="Left", club_team_id=3, nationality_id=10,
            ),
            User(
                id=11, tenant_id=1, username="arsenal-manager",
                username_normalized="arsenal-manager", password_hash=hash_password("password"),
                role=UserRole.MANAGER, is_active=True,
            ),
            User(
                id=22, tenant_id=2, username="chelsea-manager",
                username_normalized="chelsea-manager", password_hash=hash_password("password"),
                role=UserRole.MANAGER, is_active=True,
            ),
            TeamTactic(
                tenant_id=1, formation=Formation.FOUR_THREE_THREE,
                playing_style=PlayingStyle.HIGH_PRESS, notes="Press from the front",
            ),
            TeamEvent(
                tenant_id=1, created_by_user_id=11, event_type=TeamEventType.MEDICAL,
                player_id=101, injury_date=date(2026, 8, 1), description="Ankle injury",
                recovery_days=14,
            ),
            TeamEvent(
                tenant_id=2, created_by_user_id=22, event_type=TeamEventType.MEDICAL,
                player_id=102, injury_date=date(2026, 8, 2), description="Private rival injury",
                recovery_days=30,
            ),
        ])
        db.commit()

    app = create_app()

    async def override_session():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db_session] = override_session
    valid_headers = {
        "X-Agent-Service-Token": "test-service-secret",
        "X-Tenant-ID": "1",
        "X-User-ID": "11",
    }

    async def scenario() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            unauthorized = await client.get(
                "/api/internal/agent-tools/squad",
                headers={**valid_headers, "X-Agent-Service-Token": "wrong"},
            )
            assert unauthorized.status_code == 401

            forged_tenant = await client.get(
                "/api/internal/agent-tools/squad",
                headers={**valid_headers, "X-Tenant-ID": "2"},
            )
            assert forged_tenant.status_code == 403

            squad = await client.get("/api/internal/agent-tools/squad", headers=valid_headers)
            assert squad.status_code == 200
            assert [player["player_id"] for player in squad.json()["players"]] == [101]
            assert squad.json()["players"][0]["overall"] == "A"
            assert "player_face_url" not in squad.json()["players"][0]

            tactic = await client.get("/api/internal/agent-tools/tactic", headers=valid_headers)
            assert tactic.json()["formation"] == "4-3-3"
            assert "updated_by" not in tactic.json()

            injuries = await client.post(
                "/api/internal/agent-tools/injuries",
                headers=valid_headers,
                json={"from_date": "2026-08-01", "to_date": "2026-08-31"},
            )
            assert injuries.json()["total"] == 1
            assert injuries.json()["items"][0]["description"] == "Ankle injury"

            candidates = await client.post(
                "/api/internal/agent-tools/players/search",
                headers=valid_headers,
                json={
                    "positions": ["RW"], "max_age": 23,
                    "max_value_eur": 30_000_000, "minimum_overall": "A", "limit": 5,
                },
            )
            assert candidates.status_code == 200
            assert [player["player_id"] for player in candidates.json()["items"]] == [103]
            assert candidates.json()["items"][0]["overall"] == "A"

            candidate = await client.get(
                "/api/internal/agent-tools/players/103", headers=valid_headers
            )
            assert candidate.status_code == 200
            assert candidate.json()["player_id"] == 103
            own_player = await client.get(
                "/api/internal/agent-tools/players/101", headers=valid_headers
            )
            assert own_player.status_code == 404

            sql_attempt = await client.post(
                "/api/internal/agent-tools/players/search",
                headers=valid_headers,
                json={"sql": "DROP TABLE players"},
            )
            assert sql_attempt.status_code == 422

    try:
        asyncio.run(scenario())
    finally:
        get_settings.cache_clear()
