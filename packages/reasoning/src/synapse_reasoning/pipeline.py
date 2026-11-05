"""Single entry: reconstruct, assess, optional counterfactual and verification."""

import hashlib
import json
from datetime import datetime
from uuid import UUID

from synapse_correlation.models import CorrelationLink, Finding, Observation

from synapse_reasoning.counterfactual import ablate_repeated_network
from synapse_reasoning.hybrid import assess
from synapse_reasoning.models import ProposalKind, ReasoningAssessment, Reconstruction
from synapse_reasoning.reconstruction import reconstruct
from synapse_reasoning.verification import propose, verify_proposal


def evidence_fingerprint(event_ids: tuple[UUID, ...], engine_version: str) -> str:
    blob = json.dumps(
        {"events": [str(item) for item in sorted(event_ids, key=str)], "engine": engine_version},
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(blob).hexdigest()


def run_reasoning(
    observations: tuple[Observation, ...],
    findings: tuple[Finding, ...],
    links: tuple[CorrelationLink, ...],
    *,
    created_at: datetime,
    dataset_label: str,
    window_seconds: int,
    proposal_kind: ProposalKind = "recommend_analyst_investigation",
    authorized: bool = True,
    in_scope: bool = True,
    human_approved: bool = False,
    include_counterfactual: bool = True,
) -> tuple[Reconstruction, ReasoningAssessment]:
    reconstruction = reconstruct(
        observations,
        findings,
        links,
        created_at=created_at,
        dataset_label=dataset_label,
    )
    from synapse_reasoning import ENGINE_VERSION

    fingerprint = evidence_fingerprint(reconstruction.supporting_event_ids, ENGINE_VERSION)
    assessment = assess(reconstruction, window_seconds=window_seconds, fingerprint=fingerprint)
    counterfactual = None
    if include_counterfactual and reconstruction.observations:
        counterfactual = ablate_repeated_network(reconstruction, assessment)
    proposal = propose(
        reconstruction,
        proposal_kind,
        authorized=authorized,
        in_scope=in_scope,
        human_approved=human_approved,
    )
    verification = verify_proposal(proposal)
    filled = ReasoningAssessment(
        assessment_id=assessment.assessment_id,
        target_id=assessment.target_id,
        reconstruction_id=assessment.reconstruction_id,
        created_at=assessment.created_at,
        engine_version=assessment.engine_version,
        dataset_label=assessment.dataset_label,
        evidence_event_ids=assessment.evidence_event_ids,
        finding_types=assessment.finding_types,
        quality=assessment.quality,
        neural=assessment.neural,
        symbolic_hits=assessment.symbolic_hits,
        hypotheses=assessment.hypotheses,
        selected_hypothesis=assessment.selected_hypothesis,
        explanation=assessment.explanation,
        prediction=assessment.prediction,
        counterfactual=counterfactual,
        proposal=proposal,
        verification=verification,
        confidence=assessment.confidence,
        severity=assessment.severity,
        uncertainty=assessment.uncertainty,
        missing_evidence=assessment.missing_evidence,
        limitations=assessment.limitations,
        fingerprint=assessment.fingerprint,
        features=assessment.features,
    )
    return reconstruction, filled
