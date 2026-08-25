"""Clone the current PostgreSQL database and apply multi-tenant migrations.

The source database is never modified. PostgreSQL's template mechanism makes
an exact copy, including football data and the current Alembic revision.
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


DATABASE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_identifier(identifier: str) -> str:
    if not DATABASE_NAME_PATTERN.fullmatch(identifier):
        raise SystemExit(f"Unsafe database name: {identifier!r}")
    return f'"{identifier}"'


def postgres_environment(url) -> dict[str, str]:
    environment = os.environ.copy()
    if url.password:
        environment["PGPASSWORD"] = url.password
    return environment


def connection_arguments(url, database: str) -> list[str]:
    arguments = ["--dbname", database]
    if url.host:
        arguments.extend(["--host", url.host])
    if url.port:
        arguments.extend(["--port", str(url.port)])
    if url.username:
        arguments.extend(["--username", url.username])
    return arguments


def clone_into_empty_database(source_url, target_name: str) -> None:
    with tempfile.TemporaryDirectory(prefix="recruitment-db-") as temp_directory:
        dump_path = Path(temp_directory) / "source.dump"
        environment = postgres_environment(source_url)
        subprocess.run(
            [
                "pg_dump",
                *connection_arguments(source_url, source_url.database),
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                "--file",
                str(dump_path),
            ],
            check=True,
            env=environment,
        )
        subprocess.run(
            [
                "pg_restore",
                *connection_arguments(source_url, target_name),
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                str(dump_path),
            ],
            check=True,
            env=environment,
        )


def main() -> None:
    load_dotenv()
    source_value = os.getenv("DATABASE_URL")
    if not source_value:
        raise SystemExit("DATABASE_URL is not configured")

    source_url = make_url(source_value)
    source_name = source_url.database
    if not source_name:
        raise SystemExit("DATABASE_URL must contain a database name")
    target_name = os.getenv(
        "MULTITENANT_DATABASE_NAME", f"{source_name}_multitenant"
    )
    if target_name == source_name:
        raise SystemExit("Target database must differ from the source database")

    admin_url = source_url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": target_name},
        )
        if not exists:
            connection.exec_driver_sql(
                f"CREATE DATABASE {quote_identifier(target_name)} "
                f"WITH TEMPLATE {quote_identifier(source_name)}"
            )

    target_url = source_url.set(database=target_name)
    if exists:
        target_engine = create_engine(target_url)
        with target_engine.connect() as connection:
            table_count = connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
        if table_count:
            raise SystemExit(
                f"Database {target_name!r} is not empty; refusing to overwrite it"
            )
        clone_into_empty_database(source_url, target_name)

    alembic = Config("alembic.ini")
    alembic.set_main_option("sqlalchemy.url", target_url.render_as_string(hide_password=False))
    command.upgrade(alembic, "head")
    print(f"Created {target_name} and migrated it to the multi-tenant schema.")


if __name__ == "__main__":
    main()
