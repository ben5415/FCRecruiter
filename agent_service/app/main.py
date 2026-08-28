from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from agent_service.app.config import get_agent_settings


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str
    version: str


def create_app() -> FastAPI:
    settings = get_agent_settings()
    application = FastAPI(
        title=settings.agent_service_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    @application.get("/health", response_model=HealthResponse, tags=["health"])
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.agent_service_name,
            environment=settings.agent_environment,
            version=application.version,
        )

    return application


app = create_app()
