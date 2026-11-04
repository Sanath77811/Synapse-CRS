"""Allowlist redaction and normalization for untrusted observations.

Raw dictionaries are not telemetry. This module copies only named fields,
redacts values that the Phase 1 contract cannot represent, and then validates
the result with ``TelemetryEnvelope``. It does not read ``/proc``, open
network connections, or store observations.

Unsupported keys are discarded. They are never copied. Extra keys do not by
themselves make an otherwise valid observation fail. Missing required fields
and malformed required values are rejected. Error messages name the field,
not the raw value.
"""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from synapse_telemetry.envelope import (
    _COMM,
    BASIS,
    CONTENT_CLASS,
    EVENT_TYPES,
    PID_MAX,
    PORT_MAX,
    REDACTED_ADDRESS,
    REDACTED_COMM,
    SCHEMA_VERSION,
    SEQUENCE_MAX,
    START_TICKS_MAX,
    UID_MAX,
    TelemetryEnvelope,
    _parse_int,
    _parse_timestamp,
    _parse_uuid_v4,
    format_observed_at,
)

EventIdFactory = Callable[[], str]
Clock = Callable[[], str]

PROCESS_STARTED_FIELDS = ("pid", "ppid", "uid", "start_ticks", "comm")
PROCESS_EXITED_FIELDS = ("pid", "start_ticks")
NETWORK_FIELDS = ("protocol", "local_port", "remote_port", "remote_address", "uid", "pid")
IDENTITY_FIELDS = ("event_type", "target_id", "agent_id", "boot_id", "sequence")
OPTIONAL_IDENTITY_FIELDS = ("event_id", "observed_at")
PROTOCOLS = frozenset({"tcp", "tcp6", "udp", "udp6"})


class NormalizationError(Exception):
    """A raw observation could not be reduced to a Phase 1 envelope.

    Messages are fixed field names. They do not include raw values.
    """


def normalize_process_started(
    raw: Mapping[object, object],
    *,
    event_id_factory: EventIdFactory | None = None,
    clock: Clock | None = None,
) -> TelemetryEnvelope:
    """Redact a process-start observation and return a validated envelope."""
    return _normalize_typed("process_started", raw, event_id_factory, clock)


def normalize_process_exited(
    raw: Mapping[object, object],
    *,
    event_id_factory: EventIdFactory | None = None,
    clock: Clock | None = None,
) -> TelemetryEnvelope:
    """Redact a process-exit observation and return a validated envelope."""
    return _normalize_typed("process_exited", raw, event_id_factory, clock)


def normalize_network_connection(
    raw: Mapping[object, object],
    *,
    event_id_factory: EventIdFactory | None = None,
    clock: Clock | None = None,
) -> TelemetryEnvelope:
    """Redact a network observation and return a validated envelope."""
    return _normalize_typed("network_connection_observed", raw, event_id_factory, clock)


def normalize_observation(
    raw: Mapping[object, object],
    *,
    event_id_factory: EventIdFactory | None = None,
    clock: Clock | None = None,
) -> TelemetryEnvelope:
    """Dispatch on ``event_type`` and return a validated Phase 1 envelope."""
    if not isinstance(raw, Mapping):
        raise NormalizationError("observation must be an object")
    event_type = raw.get("event_type")
    if event_type not in EVENT_TYPES:
        raise NormalizationError("event type is unsupported")
    return _normalize_typed(str(event_type), raw, event_id_factory, clock)


def discarded_keys(raw: Mapping[object, object], event_type: str) -> tuple[str, ...]:
    """Return extra string keys that the allowlist will not copy."""
    allowed = _allowed_keys(event_type)
    names: list[str] = []
    for key in raw:
        if isinstance(key, str) and key not in allowed:
            names.append(key)
    return tuple(names)


def _normalize_typed(
    expected_type: str,
    raw: Mapping[object, object],
    event_id_factory: EventIdFactory | None,
    clock: Clock | None,
) -> TelemetryEnvelope:
    if not isinstance(raw, Mapping):
        raise NormalizationError("observation must be an object")
    declared = raw.get("event_type")
    if declared is not None and declared != expected_type:
        raise NormalizationError("event type is unsupported")
    payload = _payload_for(expected_type, raw)
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "event_id": _event_id(raw, event_id_factory),
        "event_type": expected_type,
        "target_id": _uuid_field(raw, "target_id"),
        "agent_id": _uuid_field(raw, "agent_id"),
        "boot_id": _uuid_field(raw, "boot_id"),
        "sequence": _int_field(raw, "sequence", minimum=1, maximum=SEQUENCE_MAX),
        "observed_at": _observed_at(raw, clock),
        "basis": BASIS,
        "content_class": CONTENT_CLASS,
        "payload": payload,
    }
    try:
        return TelemetryEnvelope.model_validate(envelope)
    except ValidationError:
        raise NormalizationError("normalized envelope is invalid") from None


def _payload_for(event_type: str, raw: Mapping[object, object]) -> dict[str, Any]:
    if event_type == "process_started":
        return {
            "pid": _int_field(raw, "pid", minimum=1, maximum=PID_MAX),
            "ppid": _int_field(raw, "ppid", minimum=0, maximum=PID_MAX),
            "uid": _int_field(raw, "uid", minimum=0, maximum=UID_MAX),
            "start_ticks": _int_field(raw, "start_ticks", minimum=0, maximum=START_TICKS_MAX),
            "comm": _comm(raw),
        }
    if event_type == "process_exited":
        return {
            "pid": _int_field(raw, "pid", minimum=1, maximum=PID_MAX),
            "start_ticks": _int_field(raw, "start_ticks", minimum=0, maximum=START_TICKS_MAX),
        }
    return {
        "protocol": _protocol(raw),
        "local_port": _int_field(raw, "local_port", minimum=0, maximum=PORT_MAX),
        "remote_port": _int_field(raw, "remote_port", minimum=0, maximum=PORT_MAX),
        "remote_address": _remote_address(raw),
        "uid": _int_field(raw, "uid", minimum=0, maximum=UID_MAX),
        "pid": _optional_pid(raw),
    }


def _allowed_keys(event_type: str) -> frozenset[str]:
    payload = {
        "process_started": PROCESS_STARTED_FIELDS,
        "process_exited": PROCESS_EXITED_FIELDS,
        "network_connection_observed": NETWORK_FIELDS,
    }[event_type]
    return frozenset(IDENTITY_FIELDS + OPTIONAL_IDENTITY_FIELDS + payload)


def _require(raw: Mapping[object, object], name: str) -> object:
    if name not in raw:
        raise NormalizationError(f"{name} is missing")
    return raw[name]


def _int_field(raw: Mapping[object, object], name: str, *, minimum: int, maximum: int) -> int:
    value = _require(raw, name)
    try:
        return _parse_int(value, minimum=minimum, maximum=maximum, name=name)
    except ValueError:
        raise NormalizationError(f"{name} is invalid") from None


def _uuid_field(raw: Mapping[object, object], name: str) -> str:
    value = _require(raw, name)
    try:
        return str(_parse_uuid_v4(value))
    except ValueError:
        raise NormalizationError(f"{name} is invalid") from None


def _event_id(raw: Mapping[object, object], factory: EventIdFactory | None) -> str:
    if "event_id" in raw and raw["event_id"] is not None:
        try:
            return str(_parse_uuid_v4(raw["event_id"]))
        except ValueError:
            raise NormalizationError("event_id is invalid") from None
    produced = (factory or _default_event_id)()
    try:
        return str(_parse_uuid_v4(produced))
    except ValueError:
        raise NormalizationError("event_id is invalid") from None


def _observed_at(raw: Mapping[object, object], clock: Clock | None) -> str:
    if "observed_at" in raw and raw["observed_at"] is not None:
        value: object = raw["observed_at"]
    else:
        value = (clock or _default_clock)()
    if not isinstance(value, str):
        raise NormalizationError("observed_at is invalid")
    try:
        parsed = _parse_timestamp(value)
    except ValueError:
        raise NormalizationError("observed_at is invalid") from None
    return format_observed_at(parsed)


def _comm(raw: Mapping[object, object]) -> str:
    value = _require(raw, "comm")
    if not isinstance(value, str):
        raise NormalizationError("comm is invalid")
    if _COMM.fullmatch(value) is not None:
        return value
    return REDACTED_COMM


def _protocol(raw: Mapping[object, object]) -> str:
    value = _require(raw, "protocol")
    if not isinstance(value, str) or value not in PROTOCOLS:
        raise NormalizationError("protocol is invalid")
    return value


def _remote_address(raw: Mapping[object, object]) -> str:
    value = _require(raw, "remote_address")
    if not isinstance(value, str) or value == "":
        raise NormalizationError("remote_address is invalid")
    return REDACTED_ADDRESS


def _optional_pid(raw: Mapping[object, object]) -> int | None:
    if "pid" not in raw:
        raise NormalizationError("pid is missing")
    value = raw["pid"]
    if value is None:
        return None
    try:
        return _parse_int(value, minimum=1, maximum=PID_MAX, name="pid")
    except ValueError:
        raise NormalizationError("pid is invalid") from None


def _default_event_id() -> str:
    return str(uuid4())


def _default_clock() -> str:
    return format_observed_at(datetime.now(UTC))
