"""Read and verify the append-only audit chain."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from synapse_contracts.audit import AuditEventPage, AuditEventView, ChainVerificationView
from synapse_contracts.version import CONTRACT_VERSION

from synapse_api.audit_log import to_view, verify_stored_chain
from synapse_api.auth import get_principal
from synapse_api.config import Principal
from synapse_api.db import get_db
from synapse_api.errors import ApiError
from synapse_api.models import AuditEventRow

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/events", response_model=AuditEventPage)
def get_events(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> AuditEventPage:
    total = session.scalar(select(func.count()).select_from(AuditEventRow)) or 0
    rows = session.scalars(
        select(AuditEventRow).order_by(AuditEventRow.sequence.asc()).limit(limit).offset(offset)
    ).all()
    return AuditEventPage(
        items=[to_view(row) for row in rows],
        limit=limit,
        offset=offset,
        total=int(total),
    )


@router.get("/events/{event_id}", response_model=AuditEventView)
def get_event(
    event_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> AuditEventView:
    row = session.get(AuditEventRow, event_id)
    if row is None:
        raise ApiError(404, "audit_event_not_found", "Audit event was not found.")
    return to_view(row)


@router.get("/verify", response_model=ChainVerificationView)
def get_verification(
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> ChainVerificationView:
    result = verify_stored_chain(session)
    return ChainVerificationView(
        valid=result.valid,
        event_count=result.event_count,
        head_hash=result.head_hash,
        failure_sequence=result.failure_sequence,
        failure_reason=result.failure_reason,
        contract_version=CONTRACT_VERSION,
    )
