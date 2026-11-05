"""Load enrolled evidence, run hybrid reasoning, persist derived assessments."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from synapse_contracts.reasoning import (
    AssessmentPage,
    CounterfactualView,
    EvidenceQualityView,
    ExplanationView,
    HypothesisView,
    NeuralView,
    PredictionView,
    ReasoningAssessmentView,
    ReconstructionView,
    TimelineItemView,
    VerificationView,
)
from synapse_contracts.version import CONTRACT_VERSION
from synapse_correlation.models import CorrelationLink, Finding, Observation, RiskFactor
from synapse_correlation.observations import observation_from_envelope
from synapse_reasoning.models import (
    EvidenceGraph,
    EvidenceQuality,
    ProposalKind,
    ReasoningAssessment,
    Reconstruction,
)
from synapse_reasoning.pipeline import run_reasoning
from synapse_reasoning.verification import propose, verify_proposal

from synapse_api.audit_log import append_event
from synapse_api.clock import utc_now
from synapse_api.errors import ApiError
from synapse_api.models import (
    CorrelationLinkRow,
    FindingRow,
    ReasoningAssessmentRow,
    ReasoningProposalRow,
    ReasoningReconstructionRow,
    TargetRow,
    TelemetryEventRow,
)


def run_assessment(
    session: Session,
    target_id: UUID,
    *,
    window_seconds: int,
    dataset_label: str,
    proposal_kind: ProposalKind,
    include_counterfactual: bool,
    actor: str,
) -> ReasoningAssessmentView:
    target = (
        session.execute(select(TargetRow).where(TargetRow.id == target_id).with_for_update())
        .scalars()
        .one_or_none()
    )
    if target is None:
        raise ApiError(404, "target_not_found", "Target was not found.")
    observations = _load_observations(session, target_id)
    findings = _load_findings(session, target_id)
    links = _load_links(session, target_id)
    now = utc_now()
    reconstruction, assessment = run_reasoning(
        observations,
        findings,
        links,
        created_at=now,
        dataset_label=dataset_label,
        window_seconds=window_seconds,
        proposal_kind=proposal_kind,
        authorized=True,
        in_scope=True,
        human_approved=False,
        include_counterfactual=include_counterfactual,
    )
    existing = session.execute(
        select(ReasoningAssessmentRow).where(
            ReasoningAssessmentRow.fingerprint == assessment.fingerprint
        )
    ).scalar_one_or_none()
    if existing is None:
        _insert(session, reconstruction, assessment, now)
    else:
        existing.selected_hypothesis = assessment.selected_hypothesis
        existing.confidence = assessment.confidence
        existing.severity = assessment.severity
        body = _assessment_body(assessment)
        body["id"] = str(existing.id)
        body["reconstruction_id"] = str(existing.reconstruction_id)
        existing.body = body
        existing.updated_at = now
    append_event(
        session,
        actor=actor,
        event_type="reasoning.completed",
        target_id=target_id,
        case_id=None,
        payload={
            "assessment_id": str(assessment.assessment_id),
            "hypothesis": assessment.selected_hypothesis,
            "dataset_label": dataset_label,
        },
        timestamp=now,
    )
    return assessment_view(assessment, reconstruction)


def list_assessments(session: Session, target_id: UUID, limit: int, offset: int) -> AssessmentPage:
    if session.get(TargetRow, target_id) is None:
        raise ApiError(404, "target_not_found", "Target was not found.")
    total = session.execute(
        select(func.count())
        .select_from(ReasoningAssessmentRow)
        .where(ReasoningAssessmentRow.target_id == target_id)
    ).scalar_one()
    rows = list(
        session.execute(
            select(ReasoningAssessmentRow)
            .where(ReasoningAssessmentRow.target_id == target_id)
            .order_by(ReasoningAssessmentRow.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars()
    )
    items = [_view_from_row(session, row) for row in rows]
    return AssessmentPage(items=items, limit=limit, offset=offset, total=total)


def get_assessment(session: Session, assessment_id: UUID) -> ReasoningAssessmentView:
    row = session.get(ReasoningAssessmentRow, assessment_id)
    if row is None:
        raise ApiError(404, "assessment_not_found", "Assessment was not found.")
    return _view_from_row(session, row)


def get_timeline(session: Session, assessment_id: UUID) -> ReconstructionView:
    view = get_assessment(session, assessment_id)
    recon = session.get(ReasoningReconstructionRow, view.reconstruction_id)
    if recon is None:
        raise ApiError(404, "reconstruction_not_found", "Reconstruction was not found.")
    return _recon_view(recon)


def verify_new_proposal(
    session: Session,
    assessment_id: UUID,
    *,
    kind: ProposalKind,
    authorized: bool,
    in_scope: bool,
    human_approved: bool,
    actor: str,
) -> VerificationView:
    row = session.get(ReasoningAssessmentRow, assessment_id)
    if row is None:
        raise ApiError(404, "assessment_not_found", "Assessment was not found.")
    recon_row = session.get(ReasoningReconstructionRow, row.reconstruction_id)
    if recon_row is None:
        raise ApiError(404, "reconstruction_not_found", "Reconstruction was not found.")
    reconstruction = Reconstruction(
        reconstruction_id=recon_row.id,
        target_id=recon_row.target_id,
        started_at=None,
        ended_at=None,
        agent_ids=(),
        timeline=(),
        processes=(),
        findings=(),
        links=(),
        observations=_load_observations(session, recon_row.target_id),
        supporting_event_ids=tuple(UUID(str(item)) for item in recon_row.event_ids),
        missing_evidence=tuple(str(item) for item in recon_row.missing_evidence),
        alternative_notes=(),
        quality=EvidenceQuality(
            telemetry_coverage=float(recon_row.quality["telemetry_coverage"]),
            identity_verification=float(recon_row.quality["identity_verification"]),
            lifecycle_completeness=float(recon_row.quality["lifecycle_completeness"]),
            correlation_clarity=float(recon_row.quality["correlation_clarity"]),
            timestamp_consistency=float(recon_row.quality["timestamp_consistency"]),
            reconstruction_completeness=float(recon_row.quality["reconstruction_completeness"]),
            notes=tuple(recon_row.quality.get("notes") or ()),
        ),
        graph=EvidenceGraph((), (), False),
        created_at=recon_row.created_at,
        dataset_label=recon_row.dataset_label,
    )
    proposal = propose(
        reconstruction,
        kind,
        authorized=authorized,
        in_scope=in_scope,
        human_approved=human_approved,
    )
    result = verify_proposal(proposal)
    session.add(
        ReasoningProposalRow(
            id=proposal.proposal_id,
            assessment_id=assessment_id,
            target_id=row.target_id,
            kind=kind,
            verification_status=result.status,
            solver_result=result.solver_result,
            body={
                "verification": result.explanation,
                "violated": list(result.violated),
                "constraints": list(result.constraints),
            },
            created_at=utc_now(),
        )
    )
    append_event(
        session,
        actor=actor,
        event_type="reasoning.proposal_verified",
        target_id=row.target_id,
        case_id=None,
        payload={"status": result.status, "kind": kind},
        timestamp=utc_now(),
    )
    return VerificationView(
        proposal_id=proposal.proposal_id,
        kind=kind,
        policy_version=result.policy_version,
        status=result.status,
        solver_result=result.solver_result,
        constraints=list(result.constraints),
        violated=list(result.violated),
        explanation=result.explanation,
        assumptions=result.assumptions,
    )


def _load_observations(session: Session, target_id: UUID) -> tuple[Observation, ...]:
    rows = list(
        session.execute(
            select(TelemetryEventRow)
            .where(
                TelemetryEventRow.target_id == target_id,
                TelemetryEventRow.identity_status == "enrolled",
            )
            .order_by(TelemetryEventRow.observed_at.asc())
            .limit(5000)
        ).scalars()
    )
    return tuple(observation_from_envelope(row.envelope) for row in rows)


def _load_findings(session: Session, target_id: UUID) -> tuple[Finding, ...]:
    rows = list(
        session.execute(select(FindingRow).where(FindingRow.target_id == target_id)).scalars()
    )
    items = []
    for row in rows:
        items.append(
            Finding(
                finding_type=row.finding_type,
                severity=row.severity,  # type: ignore[arg-type]
                evidence_strength=row.evidence_strength,  # type: ignore[arg-type]
                confidence=row.confidence,
                supporting_event_ids=tuple(UUID(str(item)) for item in row.supporting_event_ids),
                explanation=row.explanation,
                rules_triggered=tuple(str(item) for item in row.rules_triggered),
                missing_evidence=tuple(str(item) for item in row.missing_evidence),
                created_at=row.created_at,
                epistemic_status=row.epistemic_status,  # type: ignore[arg-type]
                risk_contribution=row.risk_contribution,
                risk_factors=tuple(
                    RiskFactor(
                        code=str(item["code"]),
                        points=int(item["points"]),
                        detail=str(item["detail"]),
                    )
                    for item in row.risk_factors
                    if isinstance(item, dict)
                ),
                target_id=row.target_id,
                agent_id=row.agent_id,
                boot_id=row.boot_id,
                subject_key=row.subject_key,
                window_seconds=row.window_seconds,
                fingerprint_material={"fingerprint": row.fingerprint},
            )
        )
    return tuple(items)


def _load_links(session: Session, target_id: UUID) -> tuple[CorrelationLink, ...]:
    rows = list(
        session.execute(
            select(CorrelationLinkRow).where(CorrelationLinkRow.target_id == target_id)
        ).scalars()
    )
    return tuple(
        CorrelationLink(
            rule_id=row.rule_id,
            left_event_id=row.left_event_id,
            right_event_id=row.right_event_id,
            target_id=row.target_id,
            agent_id=row.agent_id,
            boot_id=row.boot_id,
            process_pid=row.process_pid,
            process_start_ticks=row.process_start_ticks,
            window_seconds=row.window_seconds,
            reason=row.reason,
            left_observed_at=row.left_observed_at,
            right_observed_at=row.right_observed_at,
        )
        for row in rows
    )


def _insert(
    session: Session,
    reconstruction: Reconstruction,
    assessment: ReasoningAssessment,
    now: datetime,
) -> None:
    session.add(
        ReasoningReconstructionRow(
            id=reconstruction.reconstruction_id,
            target_id=reconstruction.target_id,
            dataset_label=reconstruction.dataset_label,
            event_ids=[str(item) for item in reconstruction.supporting_event_ids],
            quality={
                "telemetry_coverage": reconstruction.quality.telemetry_coverage,
                "identity_verification": reconstruction.quality.identity_verification,
                "lifecycle_completeness": reconstruction.quality.lifecycle_completeness,
                "correlation_clarity": reconstruction.quality.correlation_clarity,
                "timestamp_consistency": reconstruction.quality.timestamp_consistency,
                "reconstruction_completeness": reconstruction.quality.reconstruction_completeness,
                "notes": list(reconstruction.quality.notes),
            },
            timeline=[_timeline_dict(item) for item in reconstruction.timeline],
            process_count=len(reconstruction.processes),
            graph_nodes=len(reconstruction.graph.nodes),
            graph_edges=len(reconstruction.graph.edges),
            missing_evidence=list(reconstruction.missing_evidence),
            created_at=now,
        )
    )
    session.flush()
    session.add(
        ReasoningAssessmentRow(
            id=assessment.assessment_id,
            fingerprint=assessment.fingerprint,
            target_id=assessment.target_id,
            reconstruction_id=reconstruction.reconstruction_id,
            engine_version=assessment.engine_version,
            dataset_label=assessment.dataset_label,
            selected_hypothesis=assessment.selected_hypothesis,
            confidence=assessment.confidence,
            severity=assessment.severity,
            body=_assessment_body(assessment),
            created_at=now,
            updated_at=now,
        )
    )
    if assessment.proposal and assessment.verification:
        session.add(
            ReasoningProposalRow(
                id=assessment.proposal.proposal_id,
                assessment_id=assessment.assessment_id,
                target_id=assessment.target_id,
                kind=assessment.proposal.kind,
                verification_status=assessment.verification.status,
                solver_result=assessment.verification.solver_result,
                body={"explanation": assessment.verification.explanation},
                created_at=now,
            )
        )


def _timeline_dict(item) -> dict[str, Any]:
    return {
        "item_id": item.item_id,
        "timestamp": item.timestamp.isoformat(),
        "event_id": str(item.event_id) if item.event_id else None,
        "event_type": item.event_type,
        "classification": item.classification,
        "supporting_event_ids": [str(value) for value in item.supporting_event_ids],
        "description": item.description,
        "evidence_quality": item.evidence_quality,
        "uncertainty": item.uncertainty,
    }


def _assessment_body(assessment: ReasoningAssessment) -> dict[str, Any]:
    view = assessment_view(assessment, None)
    return view.model_dump(mode="json")


def assessment_view(
    assessment: ReasoningAssessment, reconstruction: Reconstruction | None
) -> ReasoningAssessmentView:
    verification = None
    if assessment.verification and assessment.proposal:
        verification = VerificationView(
            proposal_id=assessment.verification.proposal_id,
            kind=assessment.proposal.kind,
            policy_version=assessment.verification.policy_version,
            status=assessment.verification.status,
            solver_result=assessment.verification.solver_result,
            constraints=list(assessment.verification.constraints),
            violated=list(assessment.verification.violated),
            explanation=assessment.verification.explanation,
            assumptions=assessment.verification.assumptions,
        )
    prediction = None
    if assessment.prediction:
        prediction = PredictionView(
            prediction_id=assessment.prediction.prediction_id,
            horizon_seconds=assessment.prediction.horizon_seconds,
            prediction_target=assessment.prediction.prediction_target,
            predicted_value=assessment.prediction.predicted_value,
            baseline_value=assessment.prediction.baseline_value,
            uncertainty=assessment.prediction.uncertainty,
            evaluation_status=assessment.prediction.evaluation_status,
            limitations=assessment.prediction.limitations,
        )
    counterfactual = None
    if assessment.counterfactual:
        counterfactual = CounterfactualView(
            counterfactual_id=assessment.counterfactual.counterfactual_id,
            description=assessment.counterfactual.description,
            kind=assessment.counterfactual.kind,
            baseline_hypothesis=assessment.counterfactual.baseline_hypothesis,
            result_hypothesis=assessment.counterfactual.result_hypothesis,
            difference=assessment.counterfactual.difference,
            limitations=assessment.counterfactual.limitations,
        )
    return ReasoningAssessmentView(
        id=assessment.assessment_id,
        target_id=assessment.target_id,
        reconstruction_id=assessment.reconstruction_id,
        created_at=assessment.created_at,
        engine_version=assessment.engine_version,
        dataset_label=assessment.dataset_label,
        selected_hypothesis=assessment.selected_hypothesis,
        confidence=assessment.confidence,
        severity=assessment.severity,
        uncertainty=assessment.uncertainty,
        quality=EvidenceQualityView(
            telemetry_coverage=assessment.quality.telemetry_coverage,
            identity_verification=assessment.quality.identity_verification,
            lifecycle_completeness=assessment.quality.lifecycle_completeness,
            correlation_clarity=assessment.quality.correlation_clarity,
            timestamp_consistency=assessment.quality.timestamp_consistency,
            reconstruction_completeness=assessment.quality.reconstruction_completeness,
            notes=list(assessment.quality.notes),
        ),
        neural=NeuralView(
            model_id=assessment.neural.model_id,
            model_version=assessment.neural.model_version,
            unusualness_score=assessment.neural.unusualness_score,
            threshold=assessment.neural.threshold,
            unusual=assessment.neural.unusual,
            feature_contributions=[list(item) for item in assessment.neural.feature_contributions],
            limitations=assessment.neural.limitations,
        ),
        hypotheses=[
            HypothesisView(
                hypothesis_id=item.hypothesis_id,
                support=item.support,
                status=item.status,
                rationale=item.rationale,
                supporting_event_ids=list(item.supporting_event_ids),
                contradicting=list(item.contradicting),
                missing_evidence=list(item.missing_evidence),
                rules=list(item.rules),
            )
            for item in assessment.hypotheses
        ],
        explanation=ExplanationView(
            summary=assessment.explanation.summary,
            observed=assessment.explanation.observed,
            correlated=assessment.explanation.correlated,
            neural=assessment.explanation.neural,
            symbolic=assessment.explanation.symbolic,
            hypotheses=assessment.explanation.hypotheses,
            selected=assessment.explanation.selected,
            support=assessment.explanation.support,
            contradiction=assessment.explanation.contradiction,
            missing=assessment.explanation.missing,
            uncertainty=assessment.explanation.uncertainty,
            event_ids=list(assessment.explanation.event_ids),
            rule_ids=list(assessment.explanation.rule_ids),
        ),
        prediction=prediction,
        counterfactual=counterfactual,
        verification=verification,
        missing_evidence=list(assessment.missing_evidence),
        limitations=list(assessment.limitations),
        evidence_event_ids=list(assessment.evidence_event_ids),
        contract_version=CONTRACT_VERSION,
    )


def _view_from_row(session: Session, row: ReasoningAssessmentRow) -> ReasoningAssessmentView:
    return ReasoningAssessmentView.model_validate(row.body)


def _recon_view(row: ReasoningReconstructionRow) -> ReconstructionView:
    timeline = []
    for item in row.timeline:
        timeline.append(
            TimelineItemView(
                item_id=str(item["item_id"]),
                timestamp=item["timestamp"],
                event_id=UUID(item["event_id"]) if item.get("event_id") else None,
                event_type=str(item["event_type"]),
                classification=item["classification"],
                supporting_event_ids=[UUID(str(value)) for value in item["supporting_event_ids"]],
                description=str(item["description"]),
                evidence_quality=float(item["evidence_quality"]),
                uncertainty=str(item.get("uncertainty") or ""),
            )
        )
    quality = row.quality
    return ReconstructionView(
        id=row.id,
        target_id=row.target_id,
        dataset_label=row.dataset_label,
        started_at=None,
        ended_at=None,
        agent_ids=[],
        supporting_event_ids=[UUID(str(item)) for item in row.event_ids],
        missing_evidence=[str(item) for item in row.missing_evidence],
        quality=EvidenceQualityView(
            telemetry_coverage=float(quality["telemetry_coverage"]),
            identity_verification=float(quality["identity_verification"]),
            lifecycle_completeness=float(quality["lifecycle_completeness"]),
            correlation_clarity=float(quality["correlation_clarity"]),
            timestamp_consistency=float(quality["timestamp_consistency"]),
            reconstruction_completeness=float(quality["reconstruction_completeness"]),
            notes=list(quality.get("notes") or []),
        ),
        timeline=timeline,
        process_count=row.process_count,
        graph_nodes=row.graph_nodes,
        graph_edges=row.graph_edges,
        created_at=row.created_at,
    )
