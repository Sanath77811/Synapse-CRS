"""HTTP telemetry ingestion: validate, authorize, persist.

Network ingest accepts only enrolled agents. The lower-level persistence
service may still store unknown-agent evidence as unverified for laboratory
use. This module never trusts a caller-supplied public key or identity label.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session
from synapse_contracts.telemetry_ingest import TelemetryIngestRequest, TelemetryIngestView
from synapse_telemetry.envelope import TelemetryEnvelope
from synapse_telemetry.signatures import SignatureError, VerificationKey, decode_signature

from synapse_api.audit_log import append_event
from synapse_api.clock import utc_now
from synapse_api.enrollment import registered_agent
from synapse_api.errors import error_body
from synapse_api.models import TargetRow
from synapse_api.telemetry_store import PersistenceError, persist_verified_event

AUDIT_ACTOR = "telemetry-ingest"

_ERROR_STATUS = {
    "invalid_envelope": 422,
    "invalid_signature": 401,
    "unknown_agent": 403,
    "revoked_agent": 403,
    "target_mismatch": 403,
    "key_mismatch": 403,
    "inactive_target": 409,
    "event_id_conflict": 409,
    "sequence_conflict": 409,
}

_ERROR_MESSAGE = {
    "invalid_envelope": "Telemetry envelope is invalid.",
    "invalid_signature": "Telemetry signature is invalid.",
    "unknown_agent": "The agent is not enrolled.",
    "revoked_agent": "The agent is revoked.",
    "target_mismatch": "The agent is not bound to that target.",
    "key_mismatch": "The registered public key does not authorize this event.",
    "inactive_target": "Target authorization is not valid for telemetry ingest.",
    "event_id_conflict": "Event id collides with different evidence.",
    "sequence_conflict": "Agent boot sequence collides with different evidence.",
}


@dataclass(frozen=True)
class IngestHttpResult:
    status_code: int
    body: dict[str, Any]


def ingest_telemetry(session: Session, body: TelemetryIngestRequest) -> IngestHttpResult:
    """Authorize an enrolled agent and persist verified evidence."""
    envelope = body.envelope
    try:
        decode_signature(body.signature)
    except SignatureError:
        return _reject(session, envelope, "invalid_signature")

    agent = registered_agent(session, envelope.agent_id)
    if agent is None:
        return _reject(session, envelope, "unknown_agent")

    try:
        public_key = VerificationKey.from_raw_bytes(bytes.fromhex(agent.public_key_hex))
    except (SignatureError, ValueError):
        return _reject(session, envelope, "key_mismatch")

    try:
        result = persist_verified_event(session, envelope, body.signature, public_key)
    except PersistenceError as exc:
        return _reject(session, envelope, exc.code)

    if result.record.identity_status != "enrolled":
        return _reject(session, envelope, "unknown_agent")

    event_type = "telemetry.ingested" if result.status == "stored" else "telemetry.duplicate"
    append_event(
        session,
        actor=AUDIT_ACTOR,
        event_type=event_type,
        target_id=_audit_target_id(session, envelope.target_id),
        case_id=None,
        payload={
            "agent_id": str(envelope.agent_id),
            "event_id": str(envelope.event_id),
            "persistence_status": result.status,
            "identity_status": "enrolled",
        },
        timestamp=result.record.received_at,
    )
    view = TelemetryIngestView(
        event_id=result.record.event_id,
        persistence_status=result.status,
        signature_verified=True,
        identity_status="enrolled",
        event_type=result.record.event_type,
        agent_id=result.record.agent_id,
        target_id=result.record.target_id,
        received_at=result.record.received_at,
    )
    status_code = 201 if result.status == "stored" else 200
    return IngestHttpResult(status_code=status_code, body=view.model_dump(mode="json"))


def _audit_target_id(session: Session, target_id: object) -> UUID | None:
    if not isinstance(target_id, UUID):
        return None
    if session.get(TargetRow, target_id) is None:
        return None
    return target_id


def _reject(session: Session, envelope: TelemetryEnvelope, code: str) -> IngestHttpResult:
    status = _ERROR_STATUS.get(code, 400)
    message = _ERROR_MESSAGE.get(code, "The request was rejected.")
    payload = {"reason": code if code in _ERROR_MESSAGE else "rejected"}
    payload["agent_id"] = str(envelope.agent_id)
    payload["event_id"] = str(envelope.event_id)
    append_event(
        session,
        actor=AUDIT_ACTOR,
        event_type="telemetry.rejected",
        target_id=_audit_target_id(session, envelope.target_id),
        case_id=None,
        payload=payload,
        timestamp=utc_now(),
    )
    return IngestHttpResult(status_code=status, body=error_body(code, message))
