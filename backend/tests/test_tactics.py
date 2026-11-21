import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules.auth.models import Tenant, User, UserRole
from app.modules.auth.security import hash_password
from app.modules.players.models import Club
from app.shared.database import Base, get_db_session


def test_tactics_permissions_and_tenant_isolation() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        session.add_all([
            Club(club_team_id=1, club_name="Arsenal"),
            Club(club_team_id=2, club_name="Other Club"),
            Tenant(id=1, name="Arsenal", slug="arsenal", club_team_id=1),
            Tenant(id=2, name="Other", slug="other", club_team_id=2),
            User(id=1, tenant_id=1, username="manager", username_normalized="manager", password_hash=hash_password("secure-password"), role=UserRole.MANAGER, is_active=True),
            User(id=2, tenant_id=1, username="coach", username_normalized="coach", password_hash=hash_password("secure-password"), role=UserRole.COACH, is_active=True),
            User(id=3, tenant_id=1, username="player", username_normalized="player", password_hash=hash_password("secure-password"), role=UserRole.PLAYER, is_active=True),
            User(id=4, tenant_id=2, username="other", username_normalized="other", password_hash=hash_password("secure-password"), role=UserRole.MANAGER, is_active=True),
        ])
        session.commit()

    app = create_app()

    async def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session

    async def login(client: AsyncClient, username: str) -> str:
        response = await client.post(
            "/api/auth/login",
            json={"identifier": username, "password": "secure-password"},
        )
        assert response.status_code == 200
        return response.json()["csrf_token"]

    async def scenario() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as player:
            csrf = await login(player, "player")
            assert (await player.get("/api/tactics/current")).json()["formation"] is None
            forbidden = await player.put(
                "/api/tactics/current",
                headers={"X-CSRF-Token": csrf},
                json={"formation": "4-3-3", "playing_style": "balanced"},
            )
            assert forbidden.status_code == 403

        async with AsyncClient(transport=transport, base_url="http://testserver") as coach:
            csrf = await login(coach, "coach")
            updated = await coach.put(
                "/api/tactics/current",
                headers={"X-CSRF-Token": csrf},
                json={
                    "formation": "4-2-3-1",
                    "playing_style": "high_press",
                    "notes": "Press after losing possession.",
                },
            )
            assert updated.status_code == 200
            assert updated.json()["formation"] == "4-2-3-1"
            assert updated.json()["updated_by"]["username"] == "coach"

        async with AsyncClient(transport=transport, base_url="http://testserver") as manager:
            await login(manager, "manager")
            current = (await manager.get("/api/tactics/current")).json()
            assert current["playing_style"] == "high_press"

        async with AsyncClient(transport=transport, base_url="http://testserver") as other:
            await login(other, "other")
            assert (await other.get("/api/tactics/current")).json()["formation"] is None

    asyncio.run(scenario())
