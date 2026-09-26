"""Startup configuration fails closed."""

import json

import pytest
from pydantic import ValidationError
from synapse_api.config import Settings, parse_auth_tokens


def _settings(environment: str, tokens: dict[str, dict[str, str]]) -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://synapse_app:example@localhost/synapse",
        synapse_environment=environment,
        synapse_auth_tokens=json.dumps(tokens),
        synapse_cors_origins="http://localhost:5173",
    )


def test_empty_token_set_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="empty"):
        parse_auth_tokens("  ", "local")
    with pytest.raises(RuntimeError, match="non-empty"):
        parse_auth_tokens("{}", "local")


def test_short_production_token_is_rejected() -> None:
    tokens = {"short-token-value": {"actor": "admin", "role": "admin"}}
    with pytest.raises(RuntimeError, match="32"):
        parse_auth_tokens(json.dumps(tokens), "production")


def test_duplicate_actors_are_rejected() -> None:
    tokens = {
        "a" * 32: {"actor": "same", "role": "admin"},
        "b" * 32: {"actor": "same", "role": "viewer"},
    }
    with pytest.raises(RuntimeError, match="unique"):
        parse_auth_tokens(json.dumps(tokens), "local")


def test_wildcard_cors_origin_is_rejected() -> None:
    settings = _settings(
        "local",
        {"c" * 32: {"actor": "local-admin", "role": "admin"}},
    )
    settings.synapse_cors_origins = "*"
    with pytest.raises(RuntimeError, match="wildcard"):
        settings.cors_origins()


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings(
            "staging",
            {"d" * 32: {"actor": "local-admin", "role": "admin"}},
        )


def test_valid_local_settings_parse() -> None:
    settings = _settings(
        "test",
        {
            "e" * 32: {"actor": "local-admin", "role": "admin"},
            "f" * 32: {"actor": "local-viewer", "role": "viewer"},
        },
    )
    principals = settings.principals()
    assert {item.role for item in principals.values()} == {"admin", "viewer"}
