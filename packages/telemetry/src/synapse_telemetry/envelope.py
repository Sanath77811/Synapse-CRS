"""Telemetry observation contract 1.0.0.

This module validates data. It does not collect events, sign them, transport
them, or store them. A valid document is an observation, never an instruction.

The only collection basis is ``procfs_poll``. The only content class is
``observation``. Exactly three event types exist. Unknown fields are rejected
so a document cannot grow a command, shell, path, or secret channel.

Timestamps use the fixed UTC form already used by the audit chain:
``YYYY-MM-DDTHH:MM:SS.ffffffZ``. The schema pattern bounds that shape. The
model also rejects values that are not real civil timestamps, including
impossible dates such as February 31.
"""

import re
from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_serializer,
    model_validator,
)

SCHEMA_VERSION = "1.0.0"
BASIS = "procfs_poll"
CONTENT_CLASS = "observation"
EVENT_TYPES = ("process_started", "process_exited", "network_connection_observed")

PID_MAX = 4_194_304
UID_MAX = 4_294_967_295
SEQUENCE_MAX = 2**63 - 1
START_TICKS_MAX = 2**63 - 1
COMM_MAX_LENGTH = 15
PORT_MAX = 65_535
REDACTED_COMM = "[redacted]"
REDACTED_ADDRESS = "[ip]"

UUID_V4_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
TIMESTAMP_PATTERN = (
    r"^[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\.[0-9]{6}Z$"
)
COMM_PATTERN = rf"^({re.escape(REDACTED_COMM)}|[A-Za-z0-9][A-Za-z0-9._:-]{{0,14}})$"

_UUID_V4 = re.compile(UUID_V4_PATTERN)
_TIMESTAMP = re.compile(TIMESTAMP_PATTERN)
_COMM = re.compile(COMM_PATTERN)


def format_observed_at(value: datetime) -> str:
    """Format UTC with fixed width, matching the audit chain timestamp."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    utc_value = value.astimezone(UTC)
    return utc_value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc_value.microsecond:06d}Z"


def _parse_uuid_v4(value: object) -> UUID:
    if not isinstance(value, str) or _UUID_V4.fullmatch(value) is None:
        raise ValueError("must be a canonical lowercase UUID version 4")
    return UUID(value)


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or _TIMESTAMP.fullmatch(value) is None:
        raise ValueError("observed_at must be YYYY-MM-DDTHH:MM:SS.ffffffZ")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("observed_at must be a real UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    return parsed


def _parse_int(value: object, *, minimum: int, maximum: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < minimum or value > maximum:
        raise ValueError(f"{name} is outside {minimum}..{maximum}")
    return value


def _parse_sequence(value: object) -> int:
    return _parse_int(value, minimum=1, maximum=SEQUENCE_MAX, name="sequence")


def _parse_pid(value: object) -> int:
    return _parse_int(value, minimum=1, maximum=PID_MAX, name="pid")


def _parse_ppid(value: object) -> int:
    return _parse_int(value, minimum=0, maximum=PID_MAX, name="ppid")


def _parse_uid(value: object) -> int:
    return _parse_int(value, minimum=0, maximum=UID_MAX, name="uid")


def _parse_start_ticks(value: object) -> int:
    return _parse_int(value, minimum=0, maximum=START_TICKS_MAX, name="start_ticks")


def _parse_port(value: object) -> int:
    return _parse_int(value, minimum=0, maximum=PORT_MAX, name="port")


def _parse_optional_pid(value: object) -> int | None:
    if value is None:
        return None
    return _parse_pid(value)


def _parse_comm(value: object) -> str:
    if not isinstance(value, str) or _COMM.fullmatch(value) is None:
        raise ValueError("comm must be a bounded task name or [redacted]")
    return value


UuidV4 = Annotated[UUID, BeforeValidator(_parse_uuid_v4)]
ObservedAt = Annotated[datetime, BeforeValidator(_parse_timestamp)]
SequenceNumber = Annotated[int, BeforeValidator(_parse_sequence)]
Pid = Annotated[int, BeforeValidator(_parse_pid)]
ParentPid = Annotated[int, BeforeValidator(_parse_ppid)]
UserId = Annotated[int, BeforeValidator(_parse_uid)]
StartTicks = Annotated[int, BeforeValidator(_parse_start_ticks)]
Port = Annotated[int, BeforeValidator(_parse_port)]
OptionalPid = Annotated[int | None, BeforeValidator(_parse_optional_pid)]
Comm = Annotated[str, BeforeValidator(_parse_comm)]


class ProcessStartedPayload(BaseModel):
    """First poll sighting of one process identity.

    ``comm`` is the kernel task name, at most 15 characters, or the redaction
    token. It is not a command line. Arguments, environment, and paths are
    not representable.
    """

    model_config = ConfigDict(extra="forbid")

    pid: Pid
    ppid: ParentPid
    uid: UserId
    start_ticks: StartTicks
    comm: Comm


class ProcessExitedPayload(BaseModel):
    """A previously seen process identity was absent on a later poll.

    A procfs poll cannot observe an exit code, signal, or exact exit instant.
    Those values are not representable. ``start_ticks`` distinguishes pid reuse.
    """

    model_config = ConfigDict(extra="forbid")

    pid: Pid
    start_ticks: StartTicks


class NetworkConnectionObservedPayload(BaseModel):
    """One network endpoint pair observed from procfs network tables.

    ``remote_address`` is only the redaction token ``[ip]``. Raw addresses are
    not representable in this version. Packet contents, names, and headers are
    not representable. ``pid`` is null when the poll cannot map the endpoint
    to a process.
    """

    model_config = ConfigDict(extra="forbid")

    protocol: Literal["tcp", "tcp6", "udp", "udp6"]
    local_port: Port
    remote_port: Port
    remote_address: Literal["[ip]"]
    uid: UserId
    pid: OptionalPid


Payload = ProcessStartedPayload | ProcessExitedPayload | NetworkConnectionObservedPayload

_PAYLOAD_TYPES: dict[str, type[BaseModel]] = {
    "process_started": ProcessStartedPayload,
    "process_exited": ProcessExitedPayload,
    "network_connection_observed": NetworkConnectionObservedPayload,
}


class TelemetryEnvelope(BaseModel):
    """Versioned observation envelope.

    ``target_id`` uses the existing target primary-key type. ``agent_id`` and
    ``event_id`` are the same UUID form. ``boot_id`` is the same form because
    the kernel boot identifier is a random UUID. This phase does not check
    that any of those identifiers exist.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"]
    event_id: UuidV4
    event_type: Literal["process_started", "process_exited", "network_connection_observed"]
    target_id: UuidV4
    agent_id: UuidV4
    boot_id: UuidV4
    sequence: SequenceNumber
    observed_at: ObservedAt
    basis: Literal["procfs_poll"]
    content_class: Literal["observation"]
    payload: Payload = Field(description="Observation body. The shape is selected by event_type.")

    @field_serializer("observed_at", when_used="json")
    def serialize_observed_at(self, value: datetime) -> str:
        return format_observed_at(value)

    @model_validator(mode="after")
    def payload_matches_event_type(self) -> Self:
        expected = _PAYLOAD_TYPES[self.event_type]
        if type(self.payload) is not expected:
            raise ValueError("payload does not match event_type")
        return self
