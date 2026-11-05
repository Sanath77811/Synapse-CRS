"""Closed capability vocabulary for v0.1.

These names record future authorization intent. v0.1 does not implement the
capabilities, and it does not accept a general execution capability.
"""

from enum import StrEnum


class Capability(StrEnum):
    TELEMETRY_INGEST = "telemetry.ingest"
    EVIDENCE_SUBMIT = "evidence.submit"
    REASONING_REQUEST = "reasoning.request"
    VERIFICATION_REQUEST = "verification.request"


ALLOWED_CAPABILITIES = frozenset(item.value for item in Capability)
