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
    multitenant_database_url: str | None = None
    session_cookie_name: str = "recruitment_session"
    session_lifetime_hours: int = 24
    cookie_secure: bool = False
    # Agent Service 调用 Backend 内部只读 API 时使用的共享密钥。
    # 生产环境必须通过环境变量 AGENT_SERVICE_TOKEN 设置，不能提交真实值。
    agent_service_token: str | None = None
    agent_service_url: str = "http://127.0.0.1:8001"
    agent_service_timeout_seconds: float = 120.0

    @property
    def effective_database_url(self) -> str | None:
        return self.multitenant_database_url or self.database_url

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
