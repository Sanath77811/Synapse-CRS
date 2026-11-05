"""Hash-chain construction and verification.

The chain makes silent edits detectable to a reviewer who replays these
functions. It does not make the database tamper-proof: a principal who can
disable triggers, replace the table, or rewrite an external copy can rewrite
history. v0.1 documents that limit and rejects ordinary application updates.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

GENESIS_HASH = "0" * 64


def format_timestamp(value: datetime) -> str:
    """Format UTC timestamps with a fixed width so hashes survive a round trip."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    utc_value = value.astimezone(UTC)
    return utc_value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc_value.microsecond:06d}Z"


def normalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON object with stable key order and JSON-native values."""
    normalized = json.loads(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )
    if not isinstance(normalized, dict):
        raise ValueError("audit payload must be a JSON object")
    return normalized


def compute_event_hash(
    *,
    previous_event_hash: str,
    event_id: UUID,
    sequence: int,
    timestamp: datetime,
    actor: str,
    event_type: str,
    target_id: UUID | None,
    case_id: UUID | None,
    payload: Mapping[str, Any],
) -> str:
    body = {
        "actor": actor,
        "case_id": None if case_id is None else str(case_id),
        "event_id": str(event_id),
        "event_type": event_type,
        "payload": normalize_payload(payload),
        "previous_event_hash": previous_event_hash,
        "sequence": sequence,
        "target_id": None if target_id is None else str(target_id),
        "timestamp": format_timestamp(timestamp),
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditLink:
    sequence: int
    event_id: UUID
    timestamp: datetime
    actor: str
    event_type: str
    target_id: UUID | None
    case_id: UUID | None
    payload: dict[str, Any]
    previous_event_hash: str
    event_hash: str


@dataclass(frozen=True)
class ChainVerification:
    valid: bool
    event_count: int
    head_hash: str | None
    failure_sequence: int | None
    failure_reason: str | None


def verify_chain(events: Sequence[AuditLink]) -> ChainVerification:
    """Replay the chain in sequence order. The caller supplies that order."""
    previous = GENESIS_HASH
    expected_sequence = 1
    for event in events:
        if event.sequence != expected_sequence:
            return ChainVerification(
                valid=False,
                event_count=len(events),
                head_hash=None,
                failure_sequence=event.sequence,
                failure_reason="sequence_gap",
            )
        if event.previous_event_hash != previous:
            return ChainVerification(
                valid=False,
                event_count=len(events),
                head_hash=None,
                failure_sequence=event.sequence,
                failure_reason="previous_hash_mismatch",
            )
        expected_hash = compute_event_hash(
            previous_event_hash=event.previous_event_hash,
            event_id=event.event_id,
            sequence=event.sequence,
            timestamp=event.timestamp,
            actor=event.actor,
            event_type=event.event_type,
            target_id=event.target_id,
            case_id=event.case_id,
            payload=event.payload,
        )
        if expected_hash != event.event_hash:
            return ChainVerification(
                valid=False,
                event_count=len(events),
                head_hash=None,
                failure_sequence=event.sequence,
                failure_reason="hash_mismatch",
            )
        previous = event.event_hash
        expected_sequence += 1
    head = events[-1].event_hash if events else None
    return ChainVerification(
        valid=True,
        event_count=len(events),
        head_hash=head,
        failure_sequence=None,
        failure_reason=None,
    )
