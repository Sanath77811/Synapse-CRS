"""The API process must not receive the migration role's connection string."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_compose_keeps_the_migration_url_on_the_one_shot_job() -> None:
    text = (ROOT / "infra" / "docker-compose.yml").read_text()
    migrate = text.split("\n  migrate:\n", 1)[1].split("\n  api:\n", 1)[0]
    api = text.split("\n  api:\n", 1)[1].split("\nvolumes:\n", 1)[0]
    assert "MIGRATION_DATABASE_URL" in migrate
    assert "upgrade" in migrate
    assert "head" in migrate
    assert "MIGRATION_DATABASE_URL" not in api
    assert "DATABASE_URL" in api
    assert "synapse_app" in api
    entrypoint = (ROOT / "infra" / "docker" / "entrypoint.sh").read_text()
    assert "alembic" not in entrypoint
    assert "MIGRATION_DATABASE_URL must not be set" in entrypoint


def test_api_entrypoint_rejects_a_migration_url_without_echoing_it() -> None:
    env = os.environ.copy()
    env["MIGRATION_DATABASE_URL"] = (
        "postgresql+psycopg://synapse:super-secret-migration@postgres:5432/synapse"
    )
    env["DATABASE_URL"] = "postgresql+psycopg://synapse_app:app-secret@postgres:5432/synapse"
    completed = subprocess.run(
        ["sh", str(ROOT / "infra" / "docker" / "entrypoint.sh")],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
        cwd=ROOT,
    )
    assert completed.returncode != 0
    combined = completed.stdout + completed.stderr
    assert "super-secret-migration" not in combined
    assert "app-secret" not in combined
    assert "MIGRATION_DATABASE_URL must not be set" in completed.stderr


def test_api_refuses_to_start_when_the_migration_url_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from synapse_api.config import Settings, get_settings
    from synapse_api.main import create_app

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://synapse_app:example@localhost/synapse")
    monkeypatch.setenv("SYNAPSE_ENVIRONMENT", "test")
    monkeypatch.setenv("SYNAPSE_CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv(
        "SYNAPSE_AUTH_TOKENS",
        json.dumps({"e" * 32: {"actor": "local-admin", "role": "admin"}}),
    )
    monkeypatch.setenv(
        "MIGRATION_DATABASE_URL",
        "postgresql+psycopg://synapse:super-secret-migration@localhost/synapse",
    )
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as failure:
            create_app()
    finally:
        get_settings.cache_clear()
    assert "MIGRATION_DATABASE_URL" in str(failure.value)
    assert "super-secret-migration" not in str(failure.value)
    assert "migration_database_url" not in Settings.model_fields
