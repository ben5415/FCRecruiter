"""Agent Service 独立数据库连接与 Session 依赖。"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from agent_service.app.config import get_agent_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_agent_engine() -> Engine:
    url = get_agent_settings().agent_database_url
    if not url:
        raise RuntimeError("AGENT_DATABASE_URL is not configured")
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_agent_session_factory() -> sessionmaker[Session]:
    return sessionmaker(get_agent_engine(), expire_on_commit=False)


async def get_agent_db_session() -> AsyncGenerator[Session, None]:
    with get_agent_session_factory()() as session:
        yield session
