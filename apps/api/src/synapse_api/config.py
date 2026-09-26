"""Runtime configuration. Secrets come from the environment."""

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_TOKEN_LENGTH = 16
PRODUCTION_MIN_TOKEN_LENGTH = 32


@dataclass(frozen=True)
class Principal:
    actor: str
    role: Literal["admin", "viewer"]


class Settings(BaseSettings):
    """Names match environment variables. pydantic-settings is case-insensitive."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(min_length=1)
    synapse_environment: str = "local"
    synapse_auth_tokens: str
    synapse_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("synapse_environment")
    @classmethod
    def known_environment(cls, value: str) -> str:
        allowed = {"local", "test", "production"}
        if value not in allowed:
            raise ValueError(f"SYNAPSE_ENVIRONMENT must be one of {sorted(allowed)}")
        return value

    def principals(self) -> dict[str, Principal]:
        return parse_auth_tokens(self.synapse_auth_tokens, self.synapse_environment)

    def cors_origins(self) -> list[str]:
        origins = [item.strip() for item in self.synapse_cors_origins.split(",") if item.strip()]
        if not origins:
            raise RuntimeError("SYNAPSE_CORS_ORIGINS must list at least one origin")
        if "*" in origins:
            raise RuntimeError("SYNAPSE_CORS_ORIGINS must not contain a wildcard")
        return origins


def parse_auth_tokens(raw: str, environment: str) -> dict[str, Principal]:
    """Parse bearer tokens. Refuse to start when the set is empty or unsafe."""
    if not raw or not raw.strip():
        raise RuntimeError("SYNAPSE_AUTH_TOKENS is empty; refusing to start")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("SYNAPSE_AUTH_TOKENS must be a JSON object") from exc
    if not isinstance(data, dict) or not data:
        raise RuntimeError("SYNAPSE_AUTH_TOKENS must be a non-empty JSON object")

    minimum = PRODUCTION_MIN_TOKEN_LENGTH if environment == "production" else MIN_TOKEN_LENGTH
    principals: dict[str, Principal] = {}
    actors: set[str] = set()
    for token, record in data.items():
        if not isinstance(token, str) or len(token) < minimum:
            raise RuntimeError(
                f"Every API token must be at least {minimum} characters "
                f"in the {environment} environment"
            )
        if not isinstance(record, dict):
            raise RuntimeError("Each API token record must be an object with actor and role")
        actor = record.get("actor")
        role = record.get("role")
        if not isinstance(actor, str) or not actor.strip() or len(actor) > 200:
            raise RuntimeError("Each API token needs an actor name")
        if role not in {"admin", "viewer"}:
            raise RuntimeError("API token roles must be admin or viewer")
        if actor in actors:
            raise RuntimeError("API token actors must be unique so audit events name one principal")
        actors.add(actor)
        principals[token] = Principal(actor=actor, role=role)
    return principals


@lru_cache
def get_settings() -> Settings:
    try:
        settings = Settings()
    except ValidationError as exc:
        fields = sorted({str(item["loc"][0]) for item in exc.errors() if item.get("loc")})
        raise RuntimeError("Synapse-CRS configuration is incomplete: " + ", ".join(fields)) from exc
    settings.principals()
    settings.cors_origins()
    return settings
