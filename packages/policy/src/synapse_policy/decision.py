"""Fail-closed target authorization decisions.

A target is eligible for a future security action only when every check
passes. v0.1 has no security action to run; callers still use this decision
before creating or advancing a case.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from synapse_contracts.capabilities import ALLOWED_CAPABILITIES
from synapse_contracts.scope import TargetScope


@dataclass(frozen=True)
class TargetRecord:
    """Authorization inputs loaded from storage or supplied by a caller."""

    owner: str
    stored_status: str
    authorization_expiry: datetime
    capabilities: tuple[str, ...]
    scope: TargetScope | None
    scope_reasons: tuple[str, ...] = ()
    target_id: UUID | None = None


@dataclass(frozen=True)
class AuthorizationDecision:
    eligible: bool
    reasons: tuple[str, ...]
    authorization_status: str


def effective_status(stored_status: str, authorization_expiry: datetime, now: datetime) -> str:
    """Derive the status operators see. Unknown stored values are invalid."""
    if stored_status == "revoked":
        return "revoked"
    expiry_elapsed = (
        authorization_expiry.tzinfo is None
        or authorization_expiry.utcoffset() is None
        or authorization_expiry <= now
    )
    if stored_status != "active":
        return "invalid"
    if expiry_elapsed:
        return "expired"
    return "active"


def evaluate_authorization(record: TargetRecord, now: datetime) -> AuthorizationDecision:
    """Return eligibility. Any failed check makes the target ineligible."""
    reasons: list[str] = []
    if record.scope_reasons:
        reasons.extend(record.scope_reasons)
    elif record.scope is None:
        reasons.append("scope_invalid")

    if not record.owner or not record.owner.strip():
        reasons.append("owner_missing")

    if record.stored_status == "revoked":
        reasons.append("authorization_revoked")
    elif record.stored_status != "active":
        reasons.append("authorization_status_invalid")

    if (
        record.authorization_expiry.tzinfo is None
        or record.authorization_expiry.utcoffset() is None
        or record.authorization_expiry <= now
    ):
        reasons.append("authorization_expired")

    if len(record.capabilities) == 0:
        reasons.append("capabilities_empty")
    if any(capability not in ALLOWED_CAPABILITIES for capability in record.capabilities):
        reasons.append("capabilities_not_allowed")
    if len(set(record.capabilities)) != len(record.capabilities):
        reasons.append("capabilities_duplicated")

    deduped = tuple(dict.fromkeys(reasons))
    return AuthorizationDecision(
        eligible=not deduped,
        reasons=deduped,
        authorization_status=effective_status(
            record.stored_status,
            record.authorization_expiry,
            now,
        ),
    )
