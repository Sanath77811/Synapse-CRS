"""Read-only correlation and finding routes, plus an admin run trigger."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from synapse_contracts.correlation import (
    CorrelationLinkPage,
    CorrelationRunRequest,
    CorrelationRunView,
    FindingPage,
    FindingView,
    RiskSummaryView,
)

from synapse_api.auth import get_principal, require_admin
from synapse_api.config import Principal
from synapse_api.correlation import (
    get_finding,
    list_findings,
    list_links,
    risk_summary,
    run_correlation,
)
from synapse_api.db import get_db

router = APIRouter(prefix="/api/v1", tags=["correlation"])


@router.post(
    "/targets/{target_id}/correlation/runs",
    response_model=CorrelationRunView,
    status_code=201,
)
def post_correlation_run(
    target_id: UUID,
    body: CorrelationRunRequest,
    principal: Principal = Depends(require_admin),
    session: Session = Depends(get_db),
) -> CorrelationRunView:
    return run_correlation(
        session,
        target_id,
        window_seconds=body.window_seconds,
        actor=principal.actor,
    )


@router.get("/targets/{target_id}/findings", response_model=FindingPage)
def get_target_findings(
    target_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> FindingPage:
    return list_findings(session, target_id, limit, offset)


@router.get("/targets/{target_id}/correlations", response_model=CorrelationLinkPage)
def get_target_correlations(
    target_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> CorrelationLinkPage:
    return list_links(session, target_id, limit, offset)


@router.get("/targets/{target_id}/risk", response_model=RiskSummaryView)
def get_target_risk(
    target_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> RiskSummaryView:
    return risk_summary(session, target_id)


@router.get("/findings/{finding_id}", response_model=FindingView)
def get_finding_by_id(
    finding_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> FindingView:
    return get_finding(session, finding_id)
