"""Persist audit events and verify the stored chain."""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from synapse_audit import (
    GENESIS_HASH,
    AuditLink,
    ChainVerification,
    compute_event_hash,
    normalize_payload,
    verify_chain,
)
from synapse_contracts.audit import AuditEventView
from synapse_contracts.version import CONTRACT_VERSION

from synapse_api.models import AuditChainStateRow, AuditEventRow


def append_event(
    session: Session,
    *,
    actor: str,
    event_type: str,
    target_id: UUID | None,
    case_id: UUID | None,
    payload: dict[str, Any],
    timestamp: Any,
) -> AuditEventRow:
    """Append one event. The caller owns the transaction."""
    state = session.execute(
        select(AuditChainStateRow).where(AuditChainStateRow.id == 1).with_for_update()
    ).scalar_one()
    sequence = int(state.next_sequence)
    previous = state.head_hash
    event_id = uuid4()
    normalized = normalize_payload(payload)
    digest = compute_event_hash(
        previous_event_hash=previous,
        event_id=event_id,
        sequence=sequence,
        timestamp=timestamp,
        actor=actor,
        event_type=event_type,
        target_id=target_id,
        case_id=case_id,
        payload=normalized,
    )
    row = AuditEventRow(
        id=event_id,
        sequence=sequence,
        event_timestamp=timestamp,
        actor=actor,
        event_type=event_type,
        target_id=target_id,
        case_id=case_id,
        payload=normalized,
        previous_event_hash=previous,
        event_hash=digest,
    )
    session.add(row)
    state.next_sequence = sequence + 1
    state.head_hash = digest
    session.flush()
    return row


def to_link(row: AuditEventRow) -> AuditLink:
    return AuditLink(
        sequence=int(row.sequence),
        event_id=row.id,
        timestamp=row.event_timestamp,
        actor=row.actor,
        event_type=row.event_type,
        target_id=row.target_id,
        case_id=row.case_id,
        payload=dict(row.payload),
        previous_event_hash=row.previous_event_hash,
        event_hash=row.event_hash,
    )


def to_view(row: AuditEventRow) -> AuditEventView:
    return AuditEventView(
        id=row.id,
        sequence=int(row.sequence),
        timestamp=row.event_timestamp,
        actor=row.actor,
        event_type=row.event_type,
        target_id=row.target_id,
        case_id=row.case_id,
        payload=dict(row.payload),
        previous_event_hash=row.previous_event_hash,
        event_hash=row.event_hash,
        contract_version=CONTRACT_VERSION,
    )


def load_chain(session: Session) -> list[AuditLink]:
    rows = session.scalars(select(AuditEventRow).order_by(AuditEventRow.sequence.asc())).all()
    return [to_link(row) for row in rows]


def verify_stored_chain(session: Session) -> ChainVerification:
    """Replay audit events and require the chain-state head to match.

    A matching event list with a rewritten ``audit_chain_state.head_hash``
    is a failed verification. The bookkeeping row is not part of the log.
    """
    events = load_chain(session)
    result = verify_chain(events)
    if not result.valid:
        return result
    state = session.get(AuditChainStateRow, 1)
    expected_head = result.head_hash if result.head_hash is not None else GENESIS_HASH
    head_matches = state is not None and state.head_hash == expected_head
    sequence_matches = state is not None and int(state.next_sequence) == result.event_count + 1
    if head_matches and sequence_matches:
        return result
    return ChainVerification(
        valid=False,
        event_count=result.event_count,
        head_hash=None,
        failure_sequence=result.event_count or None,
        failure_reason="head_hash_mismatch" if not head_matches else "chain_state_mismatch",
    )
