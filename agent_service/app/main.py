from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from agent_service.app.config import get_agent_settings
from agent_service.app.memory.api import router as memory_router
from agent_service.app.knowledge.api import router as knowledge_router
from agent_service.app.recruitment.api import router as recruitment_router
from agent_service.app.registry.api import router as registry_router


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

    application.include_router(memory_router)
    application.include_router(recruitment_router)
    application.include_router(knowledge_router)
    application.include_router(registry_router)

    return application


app = create_app()
