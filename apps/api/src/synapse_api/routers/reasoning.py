"""Hybrid reasoning routes. Admin runs; viewers read."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from synapse_contracts.reasoning import (
    AssessmentPage,
    ProposalVerifyRequest,
    ReasoningAssessmentView,
    ReasoningRunRequest,
    ReconstructionView,
    VerificationView,
)

from synapse_api.auth import get_principal, require_admin
from synapse_api.config import Principal
from synapse_api.db import get_db
from synapse_api.reasoning import (
    get_assessment,
    get_timeline,
    list_assessments,
    run_assessment,
    verify_new_proposal,
)

router = APIRouter(prefix="/api/v1", tags=["reasoning"])


@router.post(
    "/targets/{target_id}/reasoning/assessments",
    response_model=ReasoningAssessmentView,
    status_code=201,
)
def post_assessment(
    target_id: UUID,
    body: ReasoningRunRequest,
    principal: Principal = Depends(require_admin),
    session: Session = Depends(get_db),
) -> ReasoningAssessmentView:
    return run_assessment(
        session,
        target_id,
        window_seconds=body.window_seconds,
        dataset_label=body.dataset_label,
        proposal_kind=body.proposal_kind,
        include_counterfactual=body.include_counterfactual,
        actor=principal.actor,
    )


@router.get("/targets/{target_id}/reasoning/assessments", response_model=AssessmentPage)
def get_assessments(
    target_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> AssessmentPage:
    return list_assessments(session, target_id, limit, offset)


@router.get(
    "/reasoning/assessments/{assessment_id}",
    response_model=ReasoningAssessmentView,
)
def get_assessment_route(
    assessment_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> ReasoningAssessmentView:
    return get_assessment(session, assessment_id)


@router.get(
    "/reasoning/assessments/{assessment_id}/timeline",
    response_model=ReconstructionView,
)
def get_timeline_route(
    assessment_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> ReconstructionView:
    return get_timeline(session, assessment_id)


@router.get(
    "/reasoning/assessments/{assessment_id}/explanation",
    response_model=ReasoningAssessmentView,
)
def get_explanation_route(
    assessment_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> ReasoningAssessmentView:
    return get_assessment(session, assessment_id)


@router.get(
    "/reasoning/assessments/{assessment_id}/hypotheses",
    response_model=ReasoningAssessmentView,
)
def get_hypotheses_route(
    assessment_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> ReasoningAssessmentView:
    return get_assessment(session, assessment_id)


@router.post(
    "/reasoning/assessments/{assessment_id}/decision-proposals/verify",
    response_model=VerificationView,
    status_code=201,
)
def post_verify(
    assessment_id: UUID,
    body: ProposalVerifyRequest,
    principal: Principal = Depends(require_admin),
    session: Session = Depends(get_db),
) -> VerificationView:
    return verify_new_proposal(
        session,
        assessment_id,
        kind=body.kind,
        authorized=body.authorized,
        in_scope=body.in_scope,
        human_approved=body.human_approved,
        actor=principal.actor,
    )
