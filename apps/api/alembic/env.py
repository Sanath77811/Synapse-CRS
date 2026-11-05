"""Alembic environment. The database URL comes from the environment, not this file."""

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import dotenv_values
from sqlalchemy import engine_from_config, pool

_env_file = Path(__file__).resolve().parents[3] / ".env"
if _env_file.exists():
    for _key, _value in dotenv_values(_env_file).items():
        if _value is not None and _key not in os.environ:
            os.environ[_key] = _value

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get("MIGRATION_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("MIGRATION_DATABASE_URL or DATABASE_URL is required to run migrations")

# ConfigParser treats % as interpolation. Escape passwords that were percent-encoded.
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = None


def run_migrations_offline() -> None:
    context.configure(url=database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
