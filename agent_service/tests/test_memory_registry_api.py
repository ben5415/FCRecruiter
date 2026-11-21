import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from agent_service.app.config import get_agent_settings
from agent_service.app.main import create_app
from agent_service.app.recruitment.schemas import RecruitmentReport
from agent_service.app.recruitment.prompt import RECRUITMENT_SYSTEM_PROMPT
from agent_service.app.recruitment.tools import RECRUITMENT_TOOL_NAMES
from agent_service.app.runtime.schemas import AgentRunResult
from agent_service.app.shared.database import Base, get_agent_db_session


def test_recruitment_and_thread_api_are_tenant_scoped(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_SERVICE_TOKEN", "test-agent-secret")
    get_agent_settings.cache_clear()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = create_app()
    analysis_calls = []

    class FakeRunner:
        async def run(self, **kwargs):
            analysis_calls.append(kwargs)
            return AgentRunResult[RecruitmentReport](
                output=RecruitmentReport(
                    summary="Evidence-based fake analysis",
                    uncertainty="medium",
                ),
                step_count=1,
                tool_call_count=0,
            )

    def fake_runner_factory(allowed_tools):
        analysis_calls.append({"allowed_tools": list(allowed_tools)})
        return FakeRunner()

    monkeypatch.setattr(
        "agent_service.app.recruitment.api.build_recruitment_runner",
        fake_runner_factory,
    )

    async def override_session():
        with factory() as db:
            yield db

    app.dependency_overrides[get_agent_db_session] = override_session
    service_headers = {"X-Agent-Service-Token": "test-agent-secret"}
    arsenal_headers = {
        **service_headers,
        "X-Tenant-ID": "1",
        "X-User-ID": "10",
    }

    async def scenario() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://agent"
        ) as client:
            unavailable = await client.post(
                "/recruitment/analyse", headers=arsenal_headers,
                json={"question": "Diagnose the squad and recommend a winger."},
            )
            assert unavailable.status_code == 503

            registered = await client.post(
                "/agent-definitions/recruitment/register-current", headers=service_headers,
            )
            assert registered.status_code == 201
            assert registered.json()["created"] is True
            assert registered.json()["definition"]["status"] == "draft"
            repeated = await client.post(
                "/agent-definitions/recruitment/register-current", headers=service_headers,
            )
            assert repeated.json()["created"] is False
            enabled = await client.post(
                "/agent-definitions/recruitment/versions/1/enable", headers=service_headers,
            )
            assert enabled.status_code == 200
            assert enabled.json()["status"] == "active"

            analysis = await client.post(
                "/recruitment/analyse",
                headers=arsenal_headers,
                json={"question": "Diagnose the squad and recommend a winger."},
            )
            assert analysis.status_code == 200
            assert analysis.json()["output"]["summary"] == "Evidence-based fake analysis"
            assert analysis_calls[0]["allowed_tools"] == list(RECRUITMENT_TOOL_NAMES)
            assert analysis_calls[1]["system_prompt"] == RECRUITMENT_SYSTEM_PROMPT
            assert analysis_calls[1]["context"].tenant_id == 1

            created = await client.post(
                "/threads",
                headers=arsenal_headers,
                json={"agent_key": "recruitment", "title": "Window plan"},
            )
            assert created.status_code == 201
            assert created.json()["agent_version"] == 1
            thread_id = created.json()["id"]

            message = await client.post(
                f"/threads/{thread_id}/messages",
                headers=arsenal_headers,
                json={"role": "user", "content": "We need a winger", "expected_revision": 0},
            )
            assert message.status_code == 201
            assert message.json()["thread_revision"] == 1
            stale = await client.post(
                f"/threads/{thread_id}/messages",
                headers=arsenal_headers,
                json={"role": "user", "content": "Stale", "expected_revision": 0},
            )
            assert stale.status_code == 409

            other_tenant = await client.get(
                f"/threads/{thread_id}",
                headers={**service_headers, "X-Tenant-ID": "2", "X-User-ID": "10"},
            )
            assert other_tenant.status_code == 404

    try:
        asyncio.run(scenario())
    finally:
        get_agent_settings.cache_clear()
