from __future__ import annotations

import os
import sys
from importlib import import_module
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

target_metadata = import_module("agent_code.db_metadata").metadata


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


DEFAULT_DATABASE_URL = "postgresql://admin:root@localhost:5432/test_db"


def get_database_url() -> str:
    return (
        os.getenv("DATABASE_URL")
        or config.get_main_option("sqlalchemy.url")
        or DEFAULT_DATABASE_URL
    )


def escaped_config_url(database_url: str) -> str:
    return database_url.replace("%", "%%")


def configure_context(connection=None, url: str | None = None):
    context.configure(
        connection=connection,
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        literal_binds=connection is None,
        dialect_opts={"paramstyle": "named"},
    )


def run_migrations_offline() -> None:
    configure_context(url=get_database_url())

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    database_url = get_database_url()
    config.set_main_option("sqlalchemy.url", escaped_config_url(database_url))

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        configure_context(connection=connection)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
