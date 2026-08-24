import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app


def test_health_check() -> None:
    async def request_health() -> tuple[int, dict[str, str]]:
        transport = ASGITransport(app=create_app())
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/health")
            return response.status_code, response.json()

    status_code, payload = asyncio.run(request_health())

    assert status_code == 200
    assert payload == {
        "status": "ok",
        "service": "Football Recruitment Hub API",
        "environment": "development",
    }
