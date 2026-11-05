"""Hash-chain verification detects reordering and payload edits."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from synapse_audit import GENESIS_HASH, AuditLink, compute_event_hash, verify_chain

EVENT_ID = UUID("11111111-1111-4111-8111-111111111111")
SECOND_ID = UUID("22222222-2222-4222-8222-222222222222")
TARGET_ID = UUID("33333333-3333-4333-8333-333333333333")
WHEN = datetime(2026, 9, 26, 18, 0, 1, 250000, tzinfo=UTC)


def _link(
    *,
    sequence: int,
    event_id: UUID,
    previous: str,
    event_type: str = "target.created",
    payload: dict | None = None,
) -> AuditLink:
    body = payload or {"name": "lab-app-1", "executed": False}
    digest = compute_event_hash(
        previous_event_hash=previous,
        event_id=event_id,
        sequence=sequence,
        timestamp=WHEN,
        actor="test-admin",
        event_type=event_type,
        target_id=TARGET_ID,
        case_id=None,
        payload=body,
    )
    return AuditLink(
        sequence=sequence,
        event_id=event_id,
        timestamp=WHEN,
        actor="test-admin",
        event_type=event_type,
        target_id=TARGET_ID,
        case_id=None,
        payload=body,
        previous_event_hash=previous,
        event_hash=digest,
    )


def test_empty_chain_is_valid() -> None:
    result = verify_chain([])
    assert result.valid is True
    assert result.event_count == 0
    assert result.head_hash is None


def test_two_event_chain_links_to_genesis() -> None:
    first = _link(sequence=1, event_id=EVENT_ID, previous=GENESIS_HASH)
    second = _link(
        sequence=2,
        event_id=SECOND_ID,
        previous=first.event_hash,
        event_type="target.revoked",
        payload={"authorization_status": "revoked"},
    )
    result = verify_chain([first, second])
    assert result.valid is True
    assert result.head_hash == second.event_hash
    assert first.previous_event_hash == GENESIS_HASH
    assert second.previous_event_hash == first.event_hash


def test_changed_payload_breaks_the_chain() -> None:
    first = _link(sequence=1, event_id=EVENT_ID, previous=GENESIS_HASH)
    tampered = replace(first, payload={"name": "changed", "executed": False})
    result = verify_chain([tampered])
    assert result.valid is False
    assert result.failure_reason == "hash_mismatch"
    assert result.failure_sequence == 1


def test_sequence_gap_breaks_the_chain() -> None:
    first = _link(sequence=2, event_id=EVENT_ID, previous=GENESIS_HASH)
    result = verify_chain([first])
    assert result.valid is False
    assert result.failure_reason == "sequence_gap"


def test_previous_hash_mismatch_breaks_the_chain() -> None:
    first = _link(sequence=1, event_id=EVENT_ID, previous="a" * 64)
    result = verify_chain([first])
    assert result.valid is False
    assert result.failure_reason == "previous_hash_mismatch"
