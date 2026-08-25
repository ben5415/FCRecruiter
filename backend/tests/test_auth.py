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


def test_tenant_scoped_roles_and_user_management() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        session.add_all([
            Club(club_team_id=11, club_name="Manchester United"),
            Club(club_team_id=243, club_name="Real Madrid"),
            Tenant(id=1, name="United Workspace", slug="united", club_team_id=11),
            Tenant(id=2, name="Madrid Workspace", slug="madrid", club_team_id=243),
        ])
        session.add_all([
            User(id=1, tenant_id=1, username="manager", username_normalized="manager", password_hash=hash_password("manager-password"), role=UserRole.MANAGER, is_active=True),
            User(id=2, tenant_id=1, username="member", username_normalized="member", password_hash=hash_password("member-password"), role=UserRole.PLAYER, is_active=True),
            User(id=3, tenant_id=2, username="madridmanager", username_normalized="madridmanager", password_hash=hash_password("madrid-password"), role=UserRole.MANAGER, is_active=True),
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
            login = await client.post("/api/auth/login", json={"identifier": "manager", "password": "manager-password"})
            assert login.status_code == 200
            csrf = login.json()["csrf_token"]
            assert login.json()["user"]["tenant"]["slug"] == "united"
            response = await client.post("/api/admin/users", headers={"X-CSRF-Token": csrf}, json={"username": "coach", "password": "secure-password", "role": "coach"})
            assert response.status_code == 201
            assert response.json()["role"] == "coach"
            users = (await client.get("/api/admin/users")).json()["items"]
            assert len(users) == 3
            assert all(user["tenant"]["slug"] == "united" for user in users)
            global_duplicate = await client.post("/api/admin/users", headers={"X-CSRF-Token": csrf}, json={"username": "madridmanager", "password": "secure-password", "role": "player"})
            assert global_duplicate.status_code == 409
            cross_tenant = await client.patch("/api/admin/users/3", headers={"X-CSRF-Token": csrf}, json={"is_active": False})
            assert cross_tenant.status_code == 404
            password_changed = await client.patch("/api/admin/users/2/password", headers={"X-CSRF-Token": csrf}, json={"password": "new-member-password"})
            assert password_changed.status_code == 200
            async with AsyncClient(transport=transport, base_url="http://testserver") as member_client:
                old_login = await member_client.post("/api/auth/login", json={"identifier": "member", "password": "member-password"})
                assert old_login.status_code == 401
                new_login = await member_client.post("/api/auth/login", json={"identifier": "member", "password": "new-member-password"})
                assert new_login.status_code == 200
            assert (await client.delete("/api/admin/users/1", headers={"X-CSRF-Token": csrf})).status_code == 400
            assert (await client.delete("/api/admin/users/2", headers={"X-CSRF-Token": csrf})).status_code == 200
            logout = await client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf, "Origin": "http://127.0.0.1:5173"})
            assert logout.status_code == 200
            assert (await client.get("/api/auth/me")).status_code == 401
    asyncio.run(scenario())
