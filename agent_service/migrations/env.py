from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from agent_service.app.config import get_agent_settings
from agent_service.app.shared.database import Base
from agent_service.app.memory import models as memory_models  # noqa: F401
from agent_service.app.knowledge import models as knowledge_models  # noqa: F401
from agent_service.app.observability import models as observability_models  # noqa: F401
from agent_service.app.registry import models as registry_models  # noqa: F401


config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

database_url = get_agent_settings().agent_database_url
if not database_url:
    raise RuntimeError("AGENT_DATABASE_URL is required for Agent Service migrations")
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
