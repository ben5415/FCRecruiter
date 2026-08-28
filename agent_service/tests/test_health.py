import asyncio

from httpx import ASGITransport, AsyncClient

from agent_service.app.main import create_app


def test_health_check() -> None:
    async def request_health() -> tuple[int, dict[str, str]]:
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/health")
            return response.status_code, response.json()

    status_code, payload = asyncio.run(request_health())

    assert status_code == 200
    assert payload == {
        "status": "ok",
        "service": "FCRecruiter Agent Service",
        "environment": "development",
        "version": "0.1.0",
    }
