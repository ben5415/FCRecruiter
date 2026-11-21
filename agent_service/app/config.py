from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AgentSettings(BaseSettings):
    agent_service_name: str = "FCRecruiter Agent Service"
    agent_environment: str = "development"
    agent_database_url: str | None = None
    business_backend_url: str = "http://127.0.0.1:8000/api"
    agent_service_token: str | None = None
    business_backend_timeout_seconds: float = 5.0
    embedding_api_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str | None = None
    embedding_backend: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_embedding_model: str = "bge-m3"
    local_embedding_model: str = "intfloat/multilingual-e5-small"
    local_embedding_device: str = "cpu"
    embedding_dimensions: int = 1024
    embedding_timeout_seconds: float = 20.0
    knowledge_chunk_size: int = 1200
    knowledge_chunk_overlap: int = 150
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
