"""Extract observations from stored envelopes without mutating them."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from synapse_telemetry.envelope import TelemetryEnvelope, format_observed_at

from synapse_correlation.models import Observation, ProcessIdentity


class ObservationError(Exception):
    """The stored envelope could not be read as an observation."""


def observation_from_envelope(raw: Mapping[str, Any]) -> Observation:
    try:
        envelope = TelemetryEnvelope.model_validate(dict(raw))
    except Exception as exc:
        raise ObservationError("stored envelope is not a Phase 1 observation") from exc
    return Observation(
        event_id=envelope.event_id,
        event_type=envelope.event_type,
        target_id=envelope.target_id,
        agent_id=envelope.agent_id,
        boot_id=envelope.boot_id,
        sequence=envelope.sequence,
        observed_at=envelope.observed_at,
        payload=envelope.payload.model_dump(mode="json"),
    )


def process_identity_from_payload(
    observation: Observation,
) -> ProcessIdentity | None:
    payload = observation.payload
    pid = payload.get("pid")
    start_ticks = payload.get("start_ticks")
    if observation.event_type in {"process_started", "process_exited"}:
        if not isinstance(pid, int) or not isinstance(start_ticks, int):
            return None
        return ProcessIdentity(
            agent_id=observation.agent_id,
            boot_id=observation.boot_id,
            pid=pid,
            start_ticks=start_ticks,
        )
    return None


def timestamp_text(value: datetime) -> str:
    return format_observed_at(value)


def as_uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
