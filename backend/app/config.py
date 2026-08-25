from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Football Recruitment Hub API"
    app_environment: str = "development"
    api_prefix: str = "/api"
    frontend_origin: str = "http://localhost:5173"
    database_url: str | None = None
    managed_club_id: int = 11
    session_cookie_name: str = "recruitment_session"
    session_lifetime_hours: int = 24
    cookie_secure: bool = False

    @property
    def allowed_frontend_origins(self) -> list[str]:
        origins = [self.frontend_origin.rstrip("/")]
        if self.app_environment == "development":
            origins.extend(["http://localhost:5173", "http://127.0.0.1:5173"])
        return list(dict.fromkeys(origins))

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
