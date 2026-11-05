"""Target registry routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from synapse_contracts.targets import EligibilityView, TargetCreate, TargetPage, TargetView

from synapse_api.auth import get_principal, require_admin
from synapse_api.config import Principal
from synapse_api.db import get_db
from synapse_api.services import (
    create_target,
    eligibility,
    get_target,
    list_targets,
    revoke_target,
)

router = APIRouter(prefix="/api/v1/targets", tags=["targets"])


@router.post("", response_model=TargetView, status_code=201)
def post_target(
    body: TargetCreate,
    principal: Principal = Depends(require_admin),
    session: Session = Depends(get_db),
) -> TargetView:
    return create_target(session, body, principal.actor)


@router.get("", response_model=TargetPage)
def get_targets(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> TargetPage:
    return list_targets(session, limit, offset)


@router.get("/{target_id}", response_model=TargetView)
def get_target_by_id(
    target_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> TargetView:
    return get_target(session, target_id)


@router.get("/{target_id}/eligibility", response_model=EligibilityView)
def get_target_eligibility(
    target_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> EligibilityView:
    return eligibility(session, target_id)


@router.post("/{target_id}/revocation", response_model=TargetView)
def post_revocation(
    target_id: UUID,
    principal: Principal = Depends(require_admin),
    session: Session = Depends(get_db),
) -> TargetView:
    return revoke_target(session, target_id, principal.actor)
