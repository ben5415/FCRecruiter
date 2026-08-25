from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.modules.health.api import router as health_router
from app.modules.auth.api import router as auth_router
from app.modules.admin.api import router as admin_router
from app.modules.players.api import router as players_router
from app.modules.team.api import router as team_router
from app.modules.events.api import router as events_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(admin_router, prefix=settings.api_prefix)
    app.include_router(players_router, prefix=settings.api_prefix)
    app.include_router(team_router, prefix=settings.api_prefix)
    app.include_router(events_router, prefix=settings.api_prefix)
    return app


app = create_app()
