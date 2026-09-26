"""Target and case services.

State changes are stored and audited. No service in this module starts a
process, opens a socket to a target, or applies a mitigation.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from synapse_cases import ensure_transition
from synapse_cases.transitions import InvalidTransition
from synapse_contracts.capabilities import Capability
from synapse_contracts.cases import (
    CaseCreate,
    CaseDetail,
    CasePage,
    CaseState,
    CaseTransitionRequest,
    CaseView,
    TransitionView,
)
from synapse_contracts.targets import EligibilityView, TargetCreate, TargetPage, TargetView
from synapse_contracts.version import CONTRACT_VERSION
from synapse_policy import evaluate_authorization

from synapse_api.audit_log import append_event
from synapse_api.clock import utc_now
from synapse_api.errors import ApiError
from synapse_api.models import CaseRow, CaseTransitionRow, TargetRow
from synapse_api.records import target_record

TRANSITION_NOTE = "v0.1 records the transition and does not execute a security action."


def _ensure_future(expiry: datetime, now: datetime) -> None:
    if expiry <= now:
        raise ApiError(
            422,
            "authorization_expiry_not_in_future",
            "Authorization expiry must be in the future.",
        )


def _target_view(row: TargetRow, now: datetime) -> TargetView:
    decision = evaluate_authorization(target_record(row), now)
    capabilities: list[Capability] = []
    for item in row.allowed_capabilities:
        try:
            capabilities.append(Capability(str(item)))
        except ValueError:
            continue
    scope = target_record(row).scope
    if scope is None:
        raise ApiError(
            409,
            "target_not_eligible",
            "Stored target scope failed validation.",
            {"reasons": list(decision.reasons)},
        )
    return TargetView(
        id=row.id,
        name=row.name,
        owner=row.owner,
        scope=scope,
        authorization_status=decision.authorization_status,
        authorization_expiry=row.authorization_expiry,
        allowed_capabilities=capabilities,
        eligible=decision.eligible,
        eligibility_reasons=list(decision.reasons),
        created_at=row.created_at,
        updated_at=row.updated_at,
        contract_version=CONTRACT_VERSION,
    )


def _require_target(session: Session, target_id: UUID) -> TargetRow:
    row = session.get(TargetRow, target_id)
    if row is None:
        raise ApiError(404, "target_not_found", "Target was not found.")
    return row


def _require_eligible(row: TargetRow, now: datetime) -> None:
    decision = evaluate_authorization(target_record(row), now)
    if not decision.eligible:
        raise ApiError(
            409,
            "target_not_eligible",
            "Target authorization is not valid for a security action.",
            {
                "target_id": str(row.id),
                "authorization_status": decision.authorization_status,
                "reasons": list(decision.reasons),
            },
        )


def create_target(
    session: Session,
    body: TargetCreate,
    actor: str,
    now: datetime | None = None,
) -> TargetView:
    current = now or utc_now()
    _ensure_future(body.authorization_expiry, current)
    target_id = uuid4()
    row = TargetRow(
        id=target_id,
        name=body.name,
        owner=body.owner,
        scope=body.scope.model_dump(mode="json"),
        authorization_status="active",
        authorization_expiry=body.authorization_expiry,
        allowed_capabilities=[item.value for item in body.allowed_capabilities],
        created_at=current,
        updated_at=current,
    )
    session.add(row)
    session.flush()
    append_event(
        session,
        actor=actor,
        event_type="target.created",
        target_id=target_id,
        case_id=None,
        payload={
            "name": body.name,
            "owner": body.owner,
            "authorization_status": "active",
            "allowed_capabilities": [item.value for item in body.allowed_capabilities],
        },
        timestamp=current,
    )
    return _target_view(row, current)


def list_targets(
    session: Session,
    limit: int,
    offset: int,
    now: datetime | None = None,
) -> TargetPage:
    current = now or utc_now()
    total = session.scalar(select(func.count()).select_from(TargetRow)) or 0
    rows = session.scalars(
        select(TargetRow)
        .order_by(TargetRow.created_at.desc(), TargetRow.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    return TargetPage(
        items=[_target_view(row, current) for row in rows],
        limit=limit,
        offset=offset,
        total=int(total),
    )


def get_target(session: Session, target_id: UUID, now: datetime | None = None) -> TargetView:
    current = now or utc_now()
    return _target_view(_require_target(session, target_id), current)


def eligibility(session: Session, target_id: UUID, now: datetime | None = None) -> EligibilityView:
    current = now or utc_now()
    row = _require_target(session, target_id)
    decision = evaluate_authorization(target_record(row), current)
    return EligibilityView(
        target_id=row.id,
        eligible=decision.eligible,
        authorization_status=decision.authorization_status,
        reasons=list(decision.reasons),
        evaluated_at=current,
        contract_version=CONTRACT_VERSION,
    )


def revoke_target(
    session: Session,
    target_id: UUID,
    actor: str,
    now: datetime | None = None,
) -> TargetView:
    current = now or utc_now()
    row = _require_target(session, target_id)
    if row.authorization_status == "revoked":
        raise ApiError(409, "target_already_revoked", "Target authorization is already revoked.")
    row.authorization_status = "revoked"
    row.updated_at = current
    session.flush()
    append_event(
        session,
        actor=actor,
        event_type="target.revoked",
        target_id=row.id,
        case_id=None,
        payload={"authorization_status": "revoked"},
        timestamp=current,
    )
    return _target_view(row, current)


def _transition_view(row: CaseTransitionRow) -> TransitionView:
    return TransitionView(
        id=row.id,
        case_id=row.case_id,
        from_state=CaseState(row.from_state),
        to_state=CaseState(row.to_state),
        actor=row.actor,
        reason=row.reason,
        created_at=row.created_at,
        executed=False,
    )


def _case_view(row: CaseRow) -> CaseView:
    return CaseView(
        id=row.id,
        target_id=row.target_id,
        state=CaseState(row.state),
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        contract_version=CONTRACT_VERSION,
    )


def _case_detail(session: Session, row: CaseRow) -> CaseDetail:
    transitions = session.scalars(
        select(CaseTransitionRow)
        .where(CaseTransitionRow.case_id == row.id)
        .order_by(CaseTransitionRow.created_at.asc(), CaseTransitionRow.id.asc())
    ).all()
    base = _case_view(row)
    return CaseDetail(
        **base.model_dump(),
        transitions=[_transition_view(item) for item in transitions],
    )


def _require_case(session: Session, case_id: UUID) -> CaseRow:
    row = session.execute(
        select(CaseRow).where(CaseRow.id == case_id).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise ApiError(404, "case_not_found", "Case was not found.")
    return row


def create_case(
    session: Session,
    body: CaseCreate,
    actor: str,
    now: datetime | None = None,
) -> CaseDetail:
    current = now or utc_now()
    target = _require_target(session, body.target_id)
    _require_eligible(target, current)
    case_id = uuid4()
    row = CaseRow(
        id=case_id,
        target_id=target.id,
        state=CaseState.AUTHORIZED_TARGET.value,
        created_at=current,
        updated_at=current,
        created_by=actor,
    )
    session.add(row)
    session.flush()
    append_event(
        session,
        actor=actor,
        event_type="case.created",
        target_id=target.id,
        case_id=case_id,
        payload={
            "state": CaseState.AUTHORIZED_TARGET.value,
            "reason": body.reason,
            "executed": False,
        },
        timestamp=current,
    )
    return _case_detail(session, row)


def list_cases(session: Session, limit: int, offset: int) -> CasePage:
    total = session.scalar(select(func.count()).select_from(CaseRow)) or 0
    rows = session.scalars(
        select(CaseRow)
        .order_by(CaseRow.created_at.desc(), CaseRow.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    return CasePage(
        items=[_case_view(row) for row in rows],
        limit=limit,
        offset=offset,
        total=int(total),
    )


def get_case(session: Session, case_id: UUID) -> CaseDetail:
    row = session.get(CaseRow, case_id)
    if row is None:
        raise ApiError(404, "case_not_found", "Case was not found.")
    return _case_detail(session, row)


def transition_case(
    session: Session,
    case_id: UUID,
    body: CaseTransitionRequest,
    actor: str,
    now: datetime | None = None,
) -> CaseDetail:
    current = now or utc_now()
    row = _require_case(session, case_id)
    target = _require_target(session, row.target_id)
    _require_eligible(target, current)
    current_state = CaseState(row.state)
    try:
        ensure_transition(current_state, body.to_state)
    except InvalidTransition as exc:
        raise ApiError(
            409,
            "invalid_transition",
            "That case transition is not allowed.",
            {
                "from_state": exc.current.value,
                "to_state": exc.proposed.value,
                "allowed_to_state": None if exc.allowed is None else exc.allowed.value,
            },
        ) from exc
    row.state = body.to_state.value
    row.updated_at = current
    transition = CaseTransitionRow(
        id=uuid4(),
        case_id=row.id,
        from_state=current_state.value,
        to_state=body.to_state.value,
        actor=actor,
        reason=body.reason,
        created_at=current,
    )
    session.add(transition)
    session.flush()
    append_event(
        session,
        actor=actor,
        event_type="case.transition",
        target_id=row.target_id,
        case_id=row.id,
        payload={
            "from_state": current_state.value,
            "to_state": body.to_state.value,
            "reason": body.reason,
            "executed": False,
            "note": TRANSITION_NOTE,
        },
        timestamp=current,
    )
    return _case_detail(session, row)
