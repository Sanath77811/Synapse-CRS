"""Persist cryptographically verified telemetry evidence.

A stored row means Ed25519 verification succeeded for the supplied public
key. identity_status is derived from registered agents and current target
eligibility. Callers cannot supply it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from synapse_telemetry.canonical import canonical_event_bytes, canonical_json_bytes
from synapse_telemetry.envelope import EVENT_TYPES, TelemetryEnvelope
from synapse_telemetry.signatures import (
    SignatureError,
    VerificationKey,
    public_key_fingerprint,
    verify_event,
)

from synapse_api.clock import utc_now
from synapse_api.enrollment import evaluate_identity
from synapse_api.models import TelemetryEventRow

IDENTITY_STATUS = "unverified"
IDENTITY_STATUS_ENROLLED = "enrolled"
PAGE_MIN = 1
PAGE_MAX = 100


class PersistenceError(Exception):
    """A telemetry evidence operation could not be completed.

    Messages do not include signatures, keys, or envelope bodies.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class TelemetryEvidenceView:
    id: UUID
    event_id: UUID
    target_id: UUID
    agent_id: UUID
    boot_id: UUID
    event_type: str
    sequence: int
    observed_at: datetime
    schema_version: str
    envelope: dict[str, Any]
    signature: str
    public_key_hex: str
    public_key_fingerprint: str
    signature_verified: bool
    identity_status: str
    received_at: datetime


@dataclass(frozen=True)
class PersistResult:
    status: Literal["stored", "duplicate"]
    record: TelemetryEvidenceView


@dataclass(frozen=True)
class TelemetryEvidencePage:
    items: list[TelemetryEvidenceView]
    limit: int
    offset: int
    total: int


def persist_verified_event(
    session: Session,
    event: TelemetryEnvelope | Mapping[str, object],
    signature: str,
    public_key: VerificationKey,
    *,
    received_at: datetime | None = None,
) -> PersistResult:
    """Verify the signature, then derive identity, then insert.

    Caller-supplied verification flags and identity labels are ignored.
    """
    if not isinstance(public_key, VerificationKey):
        raise PersistenceError("invalid_signature", "telemetry verification key is invalid")
    try:
        envelope = (
            event
            if isinstance(event, TelemetryEnvelope)
            else TelemetryEnvelope.model_validate(dict(event))
        )
    except (ValidationError, TypeError, ValueError):
        raise PersistenceError("invalid_envelope", "telemetry envelope is invalid") from None
    try:
        verify_event(public_key, envelope, signature)
    except SignatureError:
        raise PersistenceError("invalid_signature", "telemetry signature is invalid") from None
    except ValidationError:
        raise PersistenceError("invalid_envelope", "telemetry envelope is invalid") from None

    document = envelope.model_dump(mode="json")
    key_hex = public_key.raw_bytes().hex()
    fingerprint = public_key_fingerprint(public_key)
    received = received_at or utc_now()
    decision = evaluate_identity(
        session,
        envelope.agent_id,
        envelope.target_id,
        public_key,
        received,
    )
    if decision.status == "unknown_agent":
        identity_status = IDENTITY_STATUS
    elif decision.status == "enrolled":
        identity_status = IDENTITY_STATUS_ENROLLED
    else:
        raise PersistenceError(decision.status, "agent identity is not authorized")
    row = TelemetryEventRow(
        id=uuid4(),
        event_id=envelope.event_id,
        target_id=envelope.target_id,
        agent_id=envelope.agent_id,
        boot_id=envelope.boot_id,
        event_type=envelope.event_type,
        sequence=int(envelope.sequence),
        observed_at=envelope.observed_at,
        schema_version=envelope.schema_version,
        envelope=document,
        signature=signature,
        public_key_hex=key_hex,
        public_key_fingerprint=fingerprint,
        signature_verified=True,
        identity_status=identity_status,
        received_at=received,
    )
    nested = session.begin_nested()
    try:
        session.add(row)
        session.flush()
        nested.commit()
    except IntegrityError:
        nested.rollback()
        return _resolve_conflict(session, envelope, document, signature, key_hex)
    return PersistResult(status="stored", record=_to_view(row))


def get_event_by_id(session: Session, event_id: UUID) -> TelemetryEvidenceView | None:
    row = session.scalar(select(TelemetryEventRow).where(TelemetryEventRow.event_id == event_id))
    if row is None:
        return None
    return _to_view(row)


def list_events(
    session: Session,
    *,
    limit: int,
    offset: int,
    target_id: UUID | None = None,
    agent_id: UUID | None = None,
    event_type: str | None = None,
    observed_from: datetime | None = None,
    observed_until: datetime | None = None,
) -> TelemetryEvidencePage:
    """Return a bounded, ordered page. Callers cannot supply SQL fragments."""
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < PAGE_MIN
        or limit > PAGE_MAX
    ):
        raise PersistenceError("invalid_filter", "limit is invalid")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise PersistenceError("invalid_filter", "offset is invalid")
    if event_type is not None and event_type not in EVENT_TYPES:
        raise PersistenceError("invalid_filter", "event type is invalid")
    if observed_from is not None and observed_until is not None and observed_from > observed_until:
        raise PersistenceError("invalid_filter", "time range is invalid")

    clauses = []
    if target_id is not None:
        clauses.append(TelemetryEventRow.target_id == target_id)
    if agent_id is not None:
        clauses.append(TelemetryEventRow.agent_id == agent_id)
    if event_type is not None:
        clauses.append(TelemetryEventRow.event_type == event_type)
    if observed_from is not None:
        clauses.append(TelemetryEventRow.observed_at >= observed_from)
    if observed_until is not None:
        clauses.append(TelemetryEventRow.observed_at <= observed_until)
    count_stmt = select(func.count()).select_from(TelemetryEventRow)
    list_stmt = select(TelemetryEventRow)
    if clauses:
        count_stmt = count_stmt.where(and_(*clauses))
        list_stmt = list_stmt.where(and_(*clauses))
    total = session.scalar(count_stmt) or 0
    rows = session.scalars(
        list_stmt.order_by(TelemetryEventRow.observed_at.asc(), TelemetryEventRow.event_id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    return TelemetryEvidencePage(
        items=[_to_view(row) for row in rows],
        limit=limit,
        offset=offset,
        total=int(total),
    )


def _resolve_conflict(
    session: Session,
    envelope: TelemetryEnvelope,
    document: dict[str, Any],
    signature: str,
    key_hex: str,
) -> PersistResult:
    existing = session.scalar(
        select(TelemetryEventRow).where(TelemetryEventRow.event_id == envelope.event_id)
    )
    if existing is not None:
        if _same_evidence(existing, document, signature, key_hex):
            return PersistResult(status="duplicate", record=_to_view(existing))
        raise PersistenceError("event_id_conflict", "event id collides with different evidence")
    sequenced = session.scalar(
        select(TelemetryEventRow).where(
            TelemetryEventRow.agent_id == envelope.agent_id,
            TelemetryEventRow.boot_id == envelope.boot_id,
            TelemetryEventRow.sequence == int(envelope.sequence),
        )
    )
    if sequenced is not None:
        if _same_evidence(sequenced, document, signature, key_hex):
            return PersistResult(status="duplicate", record=_to_view(sequenced))
        raise PersistenceError(
            "sequence_conflict",
            "agent boot sequence collides with different evidence",
        )
    raise PersistenceError("event_id_conflict", "telemetry evidence conflict")


def _same_evidence(
    row: TelemetryEventRow,
    document: dict[str, Any],
    signature: str,
    key_hex: str,
) -> bool:
    stored_envelope = TelemetryEnvelope.model_validate(row.envelope)
    new_envelope = TelemetryEnvelope.model_validate(document)
    return (
        canonical_event_bytes(stored_envelope) == canonical_event_bytes(new_envelope)
        and row.signature == signature
        and row.public_key_hex == key_hex
        and canonical_json_bytes(row.envelope) == canonical_json_bytes(document)
    )


def _to_view(row: TelemetryEventRow) -> TelemetryEvidenceView:
    return TelemetryEvidenceView(
        id=row.id,
        event_id=row.event_id,
        target_id=row.target_id,
        agent_id=row.agent_id,
        boot_id=row.boot_id,
        event_type=row.event_type,
        sequence=int(row.sequence),
        observed_at=row.observed_at,
        schema_version=row.schema_version,
        envelope=dict(row.envelope),
        signature=row.signature,
        public_key_hex=row.public_key_hex,
        public_key_fingerprint=row.public_key_fingerprint,
        signature_verified=bool(row.signature_verified),
        identity_status=row.identity_status,
        received_at=row.received_at,
    )
