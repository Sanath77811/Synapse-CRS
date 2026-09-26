"""Integration fixtures. Tests talk to PostgreSQL and never to a registered target."""

import json
import os
import re
import secrets
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from synapse_audit import GENESIS_HASH


class SecretMapping(dict[str, str]):
    """Dict whose repr does not include database URLs or tokens."""

    def __repr__(self) -> str:
        return "SecretMapping(redacted)"


SAFE_PASSWORD = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
TEST_DATABASE = "synapse_test"
APP_ROLE = "synapse_app"
ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv_if_present() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for key, value in dotenv_values(env_file).items():
        if value is not None and key not in os.environ:
            os.environ[key] = value


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        pytest.exit(f"{name} must be set before integration tests can run", returncode=2)
    return value


def _safe_password(value: str) -> str:
    if SAFE_PASSWORD.fullmatch(value) is None:
        pytest.exit(
            "SYNAPSE_APP_PASSWORD must be 16-128 characters from [A-Za-z0-9_-]",
            returncode=2,
        )
    return value


@pytest.fixture(scope="session")
def database() -> Generator[dict[str, str], None, None]:
    _load_dotenv_if_present()
    migration_url = _require("MIGRATION_DATABASE_URL")
    app_password = _safe_password(_require("SYNAPSE_APP_PASSWORD"))
    admin_engine = create_engine(
        make_url(migration_url).set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    with admin_engine.connect() as connection:
        role_exists = connection.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :name"),
            {"name": APP_ROLE},
        ).scalar()
        if role_exists is None:
            connection.execute(text(f"CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{app_password}'"))
        database_exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DATABASE},
        ).scalar()
        if database_exists is None:
            connection.execute(text(f"CREATE DATABASE {TEST_DATABASE}"))
        connection.execute(text(f"GRANT CONNECT ON DATABASE {TEST_DATABASE} TO {APP_ROLE}"))
    admin_engine.dispose()

    test_migration = (
        make_url(migration_url).set(database=TEST_DATABASE).render_as_string(hide_password=False)
    )
    test_app = (
        make_url(migration_url)
        .set(database=TEST_DATABASE, username=APP_ROLE, password=app_password)
        .render_as_string(hide_password=False)
    )
    os.environ["MIGRATION_DATABASE_URL"] = test_migration
    os.environ["DATABASE_URL"] = test_app
    os.environ["SYNAPSE_ENVIRONMENT"] = "test"
    os.environ["SYNAPSE_CORS_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"
    admin_token = "test-admin-" + secrets.token_hex(16)
    viewer_token = "test-viewer-" + secrets.token_hex(16)
    os.environ["SYNAPSE_AUTH_TOKENS"] = json.dumps(
        {
            admin_token: {"actor": "test-admin", "role": "admin"},
            viewer_token: {"actor": "test-viewer", "role": "viewer"},
        }
    )

    from synapse_api.config import get_settings
    from synapse_api.db import reset_engine

    get_settings.cache_clear()
    reset_engine()
    config = Config(str(ROOT / "apps" / "api" / "alembic.ini"))
    command.upgrade(config, "head")
    command.upgrade(config, "head")

    probe = create_engine(test_app)
    try:
        with probe.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.fail(
            "Could not connect as synapse_app. SYNAPSE_APP_PASSWORD must match the "
            f"existing role. error_type={type(exc).__name__}"
        )
    finally:
        probe.dispose()

    yield SecretMapping(
        {
            "admin": admin_token,
            "viewer": viewer_token,
            "migration_url": test_migration,
            "app_url": test_app,
        }
    )


def reset_tables(migration_url: str) -> None:
    engine = create_engine(migration_url)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE audit_events DISABLE TRIGGER USER"))
        connection.execute(
            text(
                "TRUNCATE TABLE audit_events, case_transitions, cases, targets "
                "RESTART IDENTITY CASCADE"
            )
        )
        connection.execute(
            text(
                "UPDATE audit_chain_state SET next_sequence = 1, head_hash = :genesis WHERE id = 1"
            ),
            {"genesis": GENESIS_HASH},
        )
        connection.execute(text("ALTER TABLE audit_events ENABLE TRIGGER USER"))
    engine.dispose()


@pytest.fixture
def tokens(database: dict[str, str]) -> dict[str, str]:
    reset_tables(database["migration_url"])
    return database


@pytest.fixture
def client(tokens: dict[str, str]):
    from fastapi.testclient import TestClient
    from synapse_api.config import get_settings
    from synapse_api.db import reset_engine
    from synapse_api.main import create_app

    get_settings.cache_clear()
    reset_engine()
    application = create_app()
    with TestClient(application) as test_client:
        yield test_client
    reset_engine()
