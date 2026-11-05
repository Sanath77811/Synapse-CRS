"""Fail-closed agent configuration from the environment."""

import os
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import UUID

from synapse_telemetry.envelope import _parse_uuid_v4


class AgentConfigError(Exception):
    """The agent refused to start because configuration is unsafe or incomplete."""


@dataclass(frozen=True)
class AgentConfig:
    agent_id: UUID
    target_id: UUID
    ingest_url: str
    home_dir: str
    poll_seconds: float
    max_pending: int
    max_state_bytes: int
    http_timeout_seconds: float
    proc_root: str


def _uuid(name: str) -> UUID:
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise AgentConfigError(f"{name} is required")
    try:
        return _parse_uuid_v4(raw)
    except ValueError as exc:
        raise AgentConfigError(f"{name} must be a canonical UUID version 4") from exc


def _positive_float(name: str, default: str) -> float:
    raw = os.environ.get(name, default).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise AgentConfigError(f"{name} must be a positive number") from exc
    if value <= 0 or value > 60:
        raise AgentConfigError(f"{name} must be in (0, 60]")
    return value


def _positive_int(name: str, default: str, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, default).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise AgentConfigError(f"{name} must be an integer") from exc
    if value < minimum or value > maximum:
        raise AgentConfigError(f"{name} is outside {minimum}..{maximum}")
    return value


def load_config() -> AgentConfig:
    ingest = os.environ.get(
        "SYNAPSE_INGEST_URL",
        "http://127.0.0.1:8000/api/v1/telemetry/ingest",
    ).strip()
    parsed = urlparse(ingest)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path == "":
        raise AgentConfigError("SYNAPSE_INGEST_URL must be an http(s) ingest URL")
    home = os.environ.get("SYNAPSE_AGENT_HOME", "").strip()
    if not home:
        raise AgentConfigError("SYNAPSE_AGENT_HOME is required")
    proc_root = os.environ.get("SYNAPSE_AGENT_PROC_ROOT", "/proc").strip() or "/proc"
    return AgentConfig(
        agent_id=_uuid("SYNAPSE_AGENT_ID"),
        target_id=_uuid("SYNAPSE_TARGET_ID"),
        ingest_url=ingest,
        home_dir=home,
        poll_seconds=_positive_float("SYNAPSE_AGENT_POLL_SECONDS", "1.0"),
        max_pending=_positive_int("SYNAPSE_AGENT_MAX_PENDING", "200", minimum=1, maximum=1000),
        max_state_bytes=_positive_int(
            "SYNAPSE_AGENT_MAX_STATE_BYTES", "524288", minimum=4096, maximum=1_048_576
        ),
        http_timeout_seconds=_positive_float("SYNAPSE_AGENT_HTTP_TIMEOUT", "10"),
        proc_root=proc_root,
    )
