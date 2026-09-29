"""Telemetry observation contracts and Ed25519 signatures.

Schema 1.0.0 describes untrusted observations. Importing this package does
not collect, transport, store, or enroll telemetry. Signing happens only
when a caller invokes it.
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
from synapse_telemetry.signatures import (
    SIGNATURE_DOMAIN,
    SIGNATURE_LENGTH,
    SignatureError,
    SigningKey,
    VerificationKey,
    generate_signing_key,
    sign_event,
    verify_event,
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
    "SIGNATURE_DOMAIN",
    "SIGNATURE_LENGTH",
    "SignatureError",
    "SigningKey",
    "TelemetryEnvelope",
    "VerificationKey",
    "format_observed_at",
    "generate_signing_key",
    "sign_event",
    "verify_event",
]
