import asyncio
from datetime import date

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules.auth.models import Tenant, User, UserRole
from app.modules.auth.security import hash_password
from app.modules.players.models import Club, Player
from app.shared.database import Base, get_db_session


def test_event_permissions_and_tenant_isolation() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        session.add_all([
            Club(club_team_id=11, club_name="Manchester United"),
            Club(club_team_id=243, club_name="Real Madrid"),
            Tenant(id=1, name="United", slug="united", club_team_id=11),
            Tenant(id=2, name="Madrid", slug="madrid", club_team_id=243),
            Player(player_id=10, short_name="United Player", club_team_id=11),
            Player(player_id=20, short_name="Madrid Player", club_team_id=243),
        ])
        roles = [UserRole.MANAGER, UserRole.DOCTOR, UserRole.COACH, UserRole.PLAYER]
        for user_id, role in enumerate(roles, start=1):
            session.add(User(
                id=user_id, tenant_id=1, username=role.value,
                username_normalized=role.value,
                password_hash=hash_password("secure-password"), role=role, is_active=True,
            ))
        session.add(User(id=5, tenant_id=2, username="madrid", username_normalized="madrid", password_hash=hash_password("secure-password"), role=UserRole.MANAGER, is_active=True))
        session.commit()

    app = create_app()
    async def override_session():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db_session] = override_session

    async def login(client: AsyncClient, username: str) -> str:
        response = await client.post("/api/auth/login", json={"identifier": username, "password": "secure-password"})
        assert response.status_code == 200
        return response.json()["csrf_token"]

    async def scenario() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as doctor:
            csrf = await login(doctor, "doctor")
            medical = await doctor.post("/api/events", headers={"X-CSRF-Token": csrf}, json={
                "event_type": "medical", "player_id": 10,
                "injury_date": "2026-08-26", "description": "Hamstring strain",
                "recovery_days": 14,
            })
            assert medical.status_code == 201
            assert medical.json()["expected_return_date"] == "2026-09-09"
            assert (await doctor.post("/api/events", headers={"X-CSRF-Token": csrf}, json={"event_type": "dressing_room", "description": "Meeting"})).status_code == 403
            assert (await doctor.delete(f"/api/events/{medical.json()['id']}", headers={"X-CSRF-Token": csrf})).status_code == 403

        async with AsyncClient(transport=transport, base_url="http://testserver") as coach:
            csrf = await login(coach, "coach")
            training = await coach.post("/api/events", headers={"X-CSRF-Token": csrf}, json={"event_type": "training", "player_id": 10, "event_date": "2026-08-26", "training_project": "Pressing", "training_effect": 8})
            assert training.status_code == 201
            assert (await coach.patch(f"/api/events/{training.json()['id']}", headers={"X-CSRF-Token": csrf}, json={"training_effect": 9})).json()["training_effect"] == 9
            below_range = await coach.patch(
                f"/api/events/{training.json()['id']}",
                headers={"X-CSRF-Token": csrf},
                json={"training_effect": -1},
            )
            above_range = await coach.patch(
                f"/api/events/{training.json()['id']}",
                headers={"X-CSRF-Token": csrf},
                json={"training_effect": 11},
            )
            assert below_range.status_code == 422
            assert above_range.status_code == 422

        async with AsyncClient(transport=transport, base_url="http://testserver") as player:
            csrf = await login(player, "player")
            dressing = await player.post("/api/events", headers={"X-CSRF-Token": csrf}, json={"event_type": "dressing_room", "event_date": "2026-08-26", "description": "Team morale improved"})
            assert dressing.status_code == 201
            assert dressing.json()["event_date"] == "2026-08-26"
            assert (await player.post("/api/events", headers={"X-CSRF-Token": csrf}, json={"event_type": "medical", "player_id": 10, "injury_date": str(date.today()), "description": "Test", "recovery_days": 1})).status_code == 403
            assert (await player.get("/api/events")).json()["total"] == 3

        async with AsyncClient(transport=transport, base_url="http://testserver") as madrid:
            await login(madrid, "madrid")
            assert (await madrid.get("/api/events")).json()["total"] == 0

        async with AsyncClient(transport=transport, base_url="http://testserver") as manager:
            csrf = await login(manager, "manager")
            events = (await manager.get("/api/events")).json()["items"]
            assert (await manager.delete(f"/api/events/{events[0]['id']}", headers={"X-CSRF-Token": csrf})).status_code == 200
    asyncio.run(scenario())
