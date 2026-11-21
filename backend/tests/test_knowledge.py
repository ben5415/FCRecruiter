import asyncio
from uuid import uuid4

import httpx
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules.auth.models import Tenant, User, UserRole
from app.modules.auth.security import hash_password
from app.modules.players.models import Club
from app.shared.database import Base, get_db_session


def test_rag_search_proxy_is_manager_only_and_uses_current_session(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        session.add(Club(club_team_id=1, club_name="Arsenal"))
        session.add(Tenant(id=4, name="Arsenal Workspace", slug="arsenal", club_team_id=1))
        session.add_all([
            User(
                id=10,
                tenant_id=4,
                username="manager",
                username_normalized="manager",
                password_hash=hash_password("manager-password"),
                role=UserRole.MANAGER,
                is_active=True,
            ),
            User(
                id=11,
                tenant_id=4,
                username="player",
                username_normalized="player",
                password_hash=hash_password("player-password"),
                role=UserRole.PLAYER,
                is_active=True,
            ),
        ])
        session.commit()

    captured = {}

    async def fake_request(method, path, manager, json=None):
        captured.update(method=method, path=path, tenant_id=manager.tenant_id, json=json)
        chunk_id = uuid4()
        return httpx.Response(200, json={
            "query": json["query"],
            "hits": [{
                "chunk_id": str(chunk_id),
                "document_id": str(uuid4()),
                "title": "Pressing",
                "source_uri": "upload://pressing.md",
                "content": "Defenders need recovery pace.",
                "similarity": 0.81,
                "chunk_index": 0,
                "metadata": {},
                "evidence_source_id": f"knowledge:{chunk_id}",
            }],
            "retrieval_ms": 18.5,
        })

    monkeypatch.setattr("app.modules.knowledge.api._request", fake_request)
    app = create_app()

    async def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session

    async def scenario() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            login = await client.post("/api/auth/login", json={
                "identifier": "manager",
                "password": "manager-password",
            })
            csrf = login.json()["csrf_token"]
            response = await client.post(
                "/api/knowledge/search",
                headers={"X-CSRF-Token": csrf},
                json={"query": "high press", "limit": 3, "min_similarity": 0.4},
            )
            assert response.status_code == 200
            assert response.json()["retrieval_ms"] == 18.5
            assert captured == {
                "method": "POST",
                "path": "/knowledge/search",
                "tenant_id": 4,
                "json": {"query": "high press", "limit": 3, "min_similarity": 0.4},
            }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            login = await client.post("/api/auth/login", json={
                "identifier": "player",
                "password": "player-password",
            })
            csrf = login.json()["csrf_token"]
            response = await client.post(
                "/api/knowledge/search",
                headers={"X-CSRF-Token": csrf},
                json={"query": "high press"},
            )
            assert response.status_code == 403

    asyncio.run(scenario())
