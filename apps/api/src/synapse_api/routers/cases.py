"""Case records and validated state transitions."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from synapse_contracts.cases import CaseCreate, CaseDetail, CasePage, CaseTransitionRequest

from synapse_api.auth import get_principal, require_admin
from synapse_api.config import Principal
from synapse_api.db import get_db
from synapse_api.services import create_case, get_case, list_cases, transition_case

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.post("", response_model=CaseDetail, status_code=201)
def post_case(
    body: CaseCreate,
    principal: Principal = Depends(require_admin),
    session: Session = Depends(get_db),
) -> CaseDetail:
    return create_case(session, body, principal.actor)


@router.get("", response_model=CasePage)
def get_cases(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> CasePage:
    return list_cases(session, limit, offset)


@router.get("/{case_id}", response_model=CaseDetail)
def get_case_by_id(
    case_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> CaseDetail:
    return get_case(session, case_id)


@router.post("/{case_id}/transitions", response_model=CaseDetail)
def post_transition(
    case_id: UUID,
    body: CaseTransitionRequest,
    principal: Principal = Depends(require_admin),
    session: Session = Depends(get_db),
) -> CaseDetail:
    return transition_case(session, case_id, body, principal.actor)
