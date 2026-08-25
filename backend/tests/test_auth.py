import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules.auth.models import User
from app.modules.auth.security import hash_password
from app.modules.players.models import Club
from app.shared.database import Base, get_db_session


def test_roles_and_admin_user_management() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        session.add_all([
            Club(club_team_id=11, club_name="Manchester United"),
            Club(club_team_id=243, club_name="Real Madrid"),
        ])
        session.add_all([
            User(id=1, username="admin", username_normalized="admin", password_hash=hash_password("admin-password"), role="admin", is_active=True, managed_club_team_id=11),
            User(id=2, username="member", username_normalized="member", password_hash=hash_password("member-password"), role="user", is_active=True, managed_club_team_id=11),
        ])
        session.commit()

    app = create_app()
    async def override_session():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db_session] = override_session

    async def scenario() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            assert (await client.get("/api/players")).status_code == 401
            member_login = await client.post("/api/auth/login", json={"identifier": "member", "password": "member-password"})
            assert member_login.status_code == 200
            assert (await client.get("/api/admin/users")).status_code == 403
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            login = await client.post("/api/auth/login", json={"identifier": "admin", "password": "admin-password"})
            csrf = login.json()["csrf_token"]
            response = await client.post("/api/admin/users", headers={"X-CSRF-Token": csrf}, json={"username": "newuser", "password": "secure-password", "role": "user", "managed_club_team_id": 11})
            assert response.status_code == 201
            assert response.json()["role"] == "user"
            assert len((await client.get("/api/admin/users")).json()["items"]) == 3
            changed = await client.patch(
                "/api/admin/users/2",
                headers={"X-CSRF-Token": csrf},
                json={"managed_club_team_id": 243},
            )
            assert changed.status_code == 200
            assert changed.json()["managed_club"]["club_name"] == "Real Madrid"
            password_changed = await client.patch(
                "/api/admin/users/2/password",
                headers={"X-CSRF-Token": csrf},
                json={"password": "new-member-password"},
            )
            assert password_changed.status_code == 200
            async with AsyncClient(transport=transport, base_url="http://testserver") as member_client:
                old_login = await member_client.post("/api/auth/login", json={"identifier": "member", "password": "member-password"})
                assert old_login.status_code == 401
                new_login = await member_client.post("/api/auth/login", json={"identifier": "member", "password": "new-member-password"})
                assert new_login.status_code == 200
            cannot_delete_self = await client.delete(
                "/api/admin/users/1", headers={"X-CSRF-Token": csrf}
            )
            assert cannot_delete_self.status_code == 400
            deleted = await client.delete(
                "/api/admin/users/2", headers={"X-CSRF-Token": csrf}
            )
            assert deleted.status_code == 200
            assert len((await client.get("/api/admin/users")).json()["items"]) == 2
            logout = await client.post(
                "/api/auth/logout",
                headers={"X-CSRF-Token": csrf, "Origin": "http://127.0.0.1:5173"},
            )
            assert logout.status_code == 200
            assert (await client.get("/api/auth/me")).status_code == 401
    asyncio.run(scenario())
