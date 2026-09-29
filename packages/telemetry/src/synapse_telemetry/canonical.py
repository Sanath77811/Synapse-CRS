"""Deterministic JSON for telemetry signatures.

The byte rules match the audit chain: UTF-8, sorted object keys, and
separators ``(",", ":")``. ``ensure_ascii`` is false, so a character is
encoded as UTF-8 rather than a ``\\u`` escape. Phase 1 field rules still
decide which characters a telemetry event may contain.

Booleans and integers stay distinct. Floats are rejected. Object key order
does not change the bytes. List order does.
"""

import json
from collections.abc import Mapping, Sequence
from typing import Any

from synapse_telemetry.envelope import TelemetryEnvelope

CANONICAL_SEPARATORS = (",", ":")


def canonical_json_bytes(value: object) -> bytes:
    """Return canonical UTF-8 JSON for a JSON-native value."""
    encoded = json.dumps(
        _json_native(value),
        sort_keys=True,
        separators=CANONICAL_SEPARATORS,
        ensure_ascii=False,
        allow_nan=False,
    )
    return encoded.encode("utf-8")


def canonical_event_bytes(event: TelemetryEnvelope) -> bytes:
    """Return the canonical bytes of one validated telemetry envelope."""
    if not isinstance(event, TelemetryEnvelope):
        raise TypeError("event must be a telemetry envelope")
    return canonical_json_bytes(event.model_dump(mode="json"))


def _json_native(value: object) -> Any:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_native(item) for item in value]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("canonical JSON object keys must be strings")
            normalized[key] = _json_native(item)
        return normalized
    raise ValueError(
        "canonical JSON only accepts objects, arrays, strings, integers, booleans, and null"
    )
