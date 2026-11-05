"""Synthetic laboratory telemetry for the offline security demonstrator.

Events are constructed to match the Phase 1 contract. They are not collected
from a host, a network, or a deployed agent.
"""

from datetime import UTC, datetime
from uuid import uuid4

from synapse_telemetry.envelope import (
    BASIS,
    CONTENT_CLASS,
    REDACTED_ADDRESS,
    SCHEMA_VERSION,
    format_observed_at,
)

LABORATORY_LABEL = "synthetic laboratory observation"


def new_uuid4() -> str:
    """Return a canonical lowercase UUID version 4 string."""
    return str(uuid4())


def laboratory_clock() -> str:
    """Return the Phase 1 UTC timestamp form for the current instant."""
    return format_observed_at(datetime.now(UTC))


def laboratory_identity() -> dict[str, str]:
    """Return shared synthetic target, agent, and boot identifiers."""
    return {
        "target_id": new_uuid4(),
        "agent_id": new_uuid4(),
        "boot_id": new_uuid4(),
    }


def envelope(
    *,
    event_type: str,
    sequence: int,
    payload: dict[str, object],
    identity: dict[str, str],
    observed_at: str,
) -> dict[str, object]:
    """Build one unsigned envelope dictionary."""
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": new_uuid4(),
        "event_type": event_type,
        "target_id": identity["target_id"],
        "agent_id": identity["agent_id"],
        "boot_id": identity["boot_id"],
        "sequence": sequence,
        "observed_at": observed_at,
        "basis": BASIS,
        "content_class": CONTENT_CLASS,
        "payload": payload,
    }


def synthetic_events(
    identity: dict[str, str] | None = None,
    observed_at: str | None = None,
) -> list[dict[str, object]]:
    """Return one synthetic event of each supported type."""
    shared = identity or laboratory_identity()
    stamp = observed_at or laboratory_clock()
    started = envelope(
        event_type="process_started",
        sequence=1,
        identity=shared,
        observed_at=stamp,
        payload={
            "pid": 4242,
            "ppid": 1,
            "uid": 1000,
            "start_ticks": 123456,
            "comm": "python3",
        },
    )
    exited = envelope(
        event_type="process_exited",
        sequence=2,
        identity=shared,
        observed_at=stamp,
        payload={"pid": 4242, "start_ticks": 123456},
    )
    network = envelope(
        event_type="network_connection_observed",
        sequence=3,
        identity=shared,
        observed_at=stamp,
        payload={
            "protocol": "tcp",
            "local_port": 40000,
            "remote_port": 443,
            "remote_address": REDACTED_ADDRESS,
            "uid": 1000,
            "pid": 4242,
        },
    )
    return [started, exited, network]


def synthetic_raw_observations(
    identity: dict[str, str] | None = None,
    observed_at: str | None = None,
) -> list[dict[str, object]]:
    """Return untrusted laboratory dictionaries, including extra and sensitive keys.

    Values are synthetic. They are not collected from a host. Extra keys exist
    so the normalizer can demonstrate allowlist extraction.
    """
    shared = identity or laboratory_identity()
    stamp = observed_at or laboratory_clock()
    started: dict[str, object] = {
        "event_type": "process_started",
        "target_id": shared["target_id"],
        "agent_id": shared["agent_id"],
        "boot_id": shared["boot_id"],
        "sequence": 1,
        "observed_at": stamp,
        "pid": 4242,
        "ppid": 1,
        "uid": 1000,
        "start_ticks": 123456,
        "comm": "python3",
        "argv": ["python3", "--version"],
        "environ": {"PATH": "/usr/bin"},
        "exe": "/usr/bin/python3",
    }
    exited: dict[str, object] = {
        "event_type": "process_exited",
        "target_id": shared["target_id"],
        "agent_id": shared["agent_id"],
        "boot_id": shared["boot_id"],
        "sequence": 2,
        "observed_at": stamp,
        "pid": 4242,
        "start_ticks": 123456,
        "exit_code": 0,
        "command": "python3",
    }
    network: dict[str, object] = {
        "event_type": "network_connection_observed",
        "target_id": shared["target_id"],
        "agent_id": shared["agent_id"],
        "boot_id": shared["boot_id"],
        "sequence": 3,
        "observed_at": stamp,
        "protocol": "tcp",
        "local_port": 40000,
        "remote_port": 443,
        "remote_address": "192.0.2.10",
        "uid": 1000,
        "pid": 4242,
        "cmdline": "curl https://192.0.2.10",
        "password": "not-a-real-secret",
    }
    return [started, exited, network]


def invalid_synthetic_event(identity: dict[str, str] | None = None) -> dict[str, object]:
    """Return a document that looks like telemetry but includes a command field."""
    events = synthetic_events(identity=identity)
    invalid = dict(events[0])
    invalid["event_id"] = new_uuid4()
    invalid["command"] = "id"
    return invalid
