"""Telemetry observation contracts for Synapse-CRS.

Schema 1.0.0 describes untrusted observations. Importing this package does
not collect, sign, transport, or store telemetry.
"""

from synapse_telemetry.envelope import (
    BASIS,
    COMM_MAX_LENGTH,
    COMM_PATTERN,
    CONTENT_CLASS,
    EVENT_TYPES,
    PID_MAX,
    PORT_MAX,
    REDACTED_ADDRESS,
    REDACTED_COMM,
    SCHEMA_VERSION,
    SEQUENCE_MAX,
    START_TICKS_MAX,
    TIMESTAMP_PATTERN,
    UID_MAX,
    UUID_V4_PATTERN,
    NetworkConnectionObservedPayload,
    ProcessExitedPayload,
    ProcessStartedPayload,
    TelemetryEnvelope,
    format_observed_at,
)

__all__ = [
    "BASIS",
    "COMM_MAX_LENGTH",
    "COMM_PATTERN",
    "CONTENT_CLASS",
    "EVENT_TYPES",
    "PID_MAX",
    "PORT_MAX",
    "REDACTED_ADDRESS",
    "REDACTED_COMM",
    "SCHEMA_VERSION",
    "SEQUENCE_MAX",
    "START_TICKS_MAX",
    "TIMESTAMP_PATTERN",
    "UID_MAX",
    "UUID_V4_PATTERN",
    "NetworkConnectionObservedPayload",
    "ProcessExitedPayload",
    "ProcessStartedPayload",
    "TelemetryEnvelope",
    "format_observed_at",
]
