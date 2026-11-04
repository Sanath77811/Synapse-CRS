"""Administrator-authorized agent enrollment and identity checks.

A registered agent is bound to one target and one current Ed25519 public key.
Signature verification is separate: this module decides whether that key is
authorized for the claimed agent and target.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from synapse_contracts.agents import AgentEnroll, AgentKeyRotate, AgentPage, AgentView
from synapse_contracts.capabilities import Capability
from synapse_policy import evaluate_authorization
from synapse_telemetry.signatures import (
    PUBLIC_KEY_LENGTH,
    SignatureError,
    VerificationKey,
    public_key_fingerprint,
)

from synapse_api.audit_log import append_event
from synapse_api.clock import utc_now
from synapse_api.errors import ApiError
from synapse_api.models import AgentRow, TargetRow
from synapse_api.records import target_record
from synapse_api.services import _lock_target, _require_eligible, _require_target

IdentityStatus = Literal[
    "enrolled",
    "unknown_agent",
    "revoked_agent",
    "target_mismatch",
    "key_mismatch",
    "inactive_target",
]


@dataclass(frozen=True)
class IdentityDecision:
    status: IdentityStatus
    agent_id: UUID
    target_id: UUID
    reasons: tuple[str, ...] = ()


def parse_public_key_hex(value: str) -> VerificationKey:
    if not isinstance(value, str) or len(value) != 64:
        raise ApiError(422, "invalid_public_key", "Public key encoding is invalid.")
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        raise ApiError(422, "invalid_public_key", "Public key encoding is invalid.") from None
    if len(raw) != PUBLIC_KEY_LENGTH or value != raw.hex():
        raise ApiError(422, "invalid_public_key", "Public key encoding is invalid.")
    try:
        return VerificationKey.from_raw_bytes(raw)
    except SignatureError:
        raise ApiError(422, "invalid_public_key", "Public key encoding is invalid.") from None


def _agent_view(row: AgentRow) -> AgentView:
    return AgentView(
        id=row.id,
        target_id=row.target_id,
        public_key_hex=row.public_key_hex,
        public_key_fingerprint=row.public_key_fingerprint,
        key_generation=int(row.key_generation),
        status=row.status,
        enrolled_at=row.enrolled_at,
        enrolled_by=row.enrolled_by,
        revoked_at=row.revoked_at,
        updated_at=row.updated_at,
    )


def _lock_agent(session: Session, agent_id: UUID) -> AgentRow | None:
    return session.execute(
        select(AgentRow)
        .where(AgentRow.id == agent_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()


def _require_telemetry_capability(row: TargetRow) -> None:
    allowed = {str(item) for item in row.allowed_capabilities}
    if Capability.TELEMETRY_INGEST.value not in allowed:
        raise ApiError(
            409,
            "target_not_eligible",
            "Target authorization is not valid for a security action.",
            {"reasons": ["telemetry_ingest_not_granted"]},
        )


def enroll_agent(
    session: Session,
    target_id: UUID,
    body: AgentEnroll,
    actor: str,
    now: datetime | None = None,
) -> AgentView:
    current = now or utc_now()
    target = _lock_target(session, target_id)
    _require_eligible(target, current)
    _require_telemetry_capability(target)
    key = parse_public_key_hex(body.public_key_hex)
    agent_id = body.agent_id or uuid4()
    row = AgentRow(
        id=agent_id,
        target_id=target.id,
        public_key_hex=key.raw_bytes().hex(),
        public_key_fingerprint=public_key_fingerprint(key),
        key_generation=1,
        status="active",
        enrolled_at=current,
        enrolled_by=actor,
        revoked_at=None,
        updated_at=current,
    )
    nested = session.begin_nested()
    try:
        session.add(row)
        session.flush()
        nested.commit()
    except IntegrityError as exc:
        nested.rollback()
        constraint = ""
        orig = getattr(exc, "orig", None)
        diag = getattr(orig, "diag", None)
        if diag is not None:
            constraint = str(getattr(diag, "constraint_name", "") or "")
        if "public_key" in constraint:
            raise ApiError(
                409,
                "public_key_already_registered",
                "That public key is already registered.",
            ) from None
        raise ApiError(409, "agent_already_enrolled", "That agent is already enrolled.") from None
    append_event(
        session,
        actor=actor,
        event_type="agent.enrolled",
        target_id=target.id,
        case_id=None,
        payload={
            "agent_id": str(row.id),
            "public_key_fingerprint": row.public_key_fingerprint,
            "key_generation": row.key_generation,
        },
        timestamp=current,
    )
    return _agent_view(row)


def rotate_agent_key(
    session: Session,
    agent_id: UUID,
    body: AgentKeyRotate,
    actor: str,
    now: datetime | None = None,
) -> AgentView:
    current = now or utc_now()
    agent = _lock_agent(session, agent_id)
    if agent is None:
        raise ApiError(404, "agent_not_found", "Agent was not found.")
    if agent.status != "active":
        raise ApiError(409, "agent_revoked", "A revoked agent cannot rotate a key.")
    target = _lock_target(session, agent.target_id)
    _require_eligible(target, current)
    _require_telemetry_capability(target)
    key = parse_public_key_hex(body.public_key_hex)
    new_hex = key.raw_bytes().hex()
    if new_hex == agent.public_key_hex:
        raise ApiError(409, "public_key_unchanged", "The replacement public key must be new.")
    previous_fingerprint = agent.public_key_fingerprint
    agent.public_key_hex = new_hex
    agent.public_key_fingerprint = public_key_fingerprint(key)
    agent.key_generation = int(agent.key_generation) + 1
    agent.updated_at = current
    nested = session.begin_nested()
    try:
        session.flush()
        nested.commit()
    except IntegrityError:
        nested.rollback()
        raise ApiError(
            409,
            "public_key_already_registered",
            "That public key is already registered.",
        ) from None
    append_event(
        session,
        actor=actor,
        event_type="agent.key_rotated",
        target_id=target.id,
        case_id=None,
        payload={
            "agent_id": str(agent.id),
            "previous_public_key_fingerprint": previous_fingerprint,
            "public_key_fingerprint": agent.public_key_fingerprint,
            "key_generation": agent.key_generation,
        },
        timestamp=current,
    )
    return _agent_view(agent)


def revoke_agent(
    session: Session,
    agent_id: UUID,
    actor: str,
    now: datetime | None = None,
) -> AgentView:
    current = now or utc_now()
    agent = _lock_agent(session, agent_id)
    if agent is None:
        raise ApiError(404, "agent_not_found", "Agent was not found.")
    if agent.status == "revoked":
        raise ApiError(409, "agent_already_revoked", "Agent is already revoked.")
    agent.status = "revoked"
    agent.revoked_at = current
    agent.updated_at = current
    session.flush()
    append_event(
        session,
        actor=actor,
        event_type="agent.revoked",
        target_id=agent.target_id,
        case_id=None,
        payload={"agent_id": str(agent.id), "status": "revoked"},
        timestamp=current,
    )
    return _agent_view(agent)


def get_agent(session: Session, agent_id: UUID) -> AgentView:
    row = session.get(AgentRow, agent_id)
    if row is None:
        raise ApiError(404, "agent_not_found", "Agent was not found.")
    return _agent_view(row)


def list_agents(session: Session, target_id: UUID, limit: int, offset: int) -> AgentPage:
    _require_target(session, target_id)
    total = (
        session.scalar(
            select(func.count()).select_from(AgentRow).where(AgentRow.target_id == target_id)
        )
        or 0
    )
    rows = session.scalars(
        select(AgentRow)
        .where(AgentRow.target_id == target_id)
        .order_by(AgentRow.enrolled_at.asc(), AgentRow.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    return AgentPage(
        items=[_agent_view(row) for row in rows],
        limit=limit,
        offset=offset,
        total=int(total),
    )


def evaluate_identity(
    session: Session,
    agent_id: UUID,
    target_id: UUID,
    public_key: VerificationKey,
    now: datetime | None = None,
) -> IdentityDecision:
    """Return the server-derived identity status. Does not trust caller labels."""
    current = now or utc_now()
    agent = _lock_agent(session, agent_id)
    if agent is None:
        return IdentityDecision(status="unknown_agent", agent_id=agent_id, target_id=target_id)
    if agent.status != "active":
        return IdentityDecision(
            status="revoked_agent",
            agent_id=agent_id,
            target_id=target_id,
            reasons=("agent_revoked",),
        )
    if agent.target_id != target_id:
        return IdentityDecision(
            status="target_mismatch",
            agent_id=agent_id,
            target_id=target_id,
            reasons=("agent_target_mismatch",),
        )
    if agent.public_key_hex != public_key.raw_bytes().hex():
        return IdentityDecision(
            status="key_mismatch",
            agent_id=agent_id,
            target_id=target_id,
            reasons=("agent_key_mismatch",),
        )
    target = session.execute(
        select(TargetRow)
        .where(TargetRow.id == target_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if target is None:
        return IdentityDecision(
            status="inactive_target",
            agent_id=agent_id,
            target_id=target_id,
            reasons=("target_not_found",),
        )
    decision = evaluate_authorization(target_record(target), current)
    allowed = {str(item) for item in target.allowed_capabilities}
    if not decision.eligible or Capability.TELEMETRY_INGEST.value not in allowed:
        return IdentityDecision(
            status="inactive_target",
            agent_id=agent_id,
            target_id=target_id,
            reasons=tuple(decision.reasons) or ("telemetry_ingest_not_granted",),
        )
    return IdentityDecision(status="enrolled", agent_id=agent_id, target_id=target_id)
