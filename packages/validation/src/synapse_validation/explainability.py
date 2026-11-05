"""Measurable explanation-quality checks. No subjective Likert scores."""

from dataclasses import asdict, dataclass
from uuid import UUID

from synapse_reasoning.explanation import build_explanation
from synapse_reasoning.hybrid import assess
from synapse_reasoning.symbolic import RULES


@dataclass(frozen=True)
class ExplanationMetrics:
    evidence_reference_validity: float
    evidence_coverage: float
    rule_traceability: float
    explanation_completeness: float
    unsupported_claim_count: int
    provenance_consistency: float
    inferred_timeline_without_event_id: bool
    notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def measure_explanation(reconstruction, assessment=None) -> ExplanationMetrics:
    if assessment is None:
        assessment = assess(reconstruction, window_seconds=300, fingerprint="explain")
    observed_ids = {item.event_id for item in reconstruction.observations}
    cited = set(assessment.evidence_event_ids)
    invalid = cited - observed_ids
    coverage = 0.0 if not observed_ids else len(cited & observed_ids) / len(observed_ids)
    known_rules = {str(row["id"]) for row in RULES}
    bad_rules = [
        rule_id for rule_id in assessment.explanation.rule_ids if rule_id not in known_rules
    ]
    inferred_ok = all(
        item.event_id is None
        for item in reconstruction.timeline
        if item.classification == "inferred"
    )
    observed_ok = all(
        item.event_id is not None
        for item in reconstruction.timeline
        if item.classification == "observed"
    )
    completeness_parts = [
        bool(assessment.explanation.summary),
        bool(assessment.explanation.observed),
        bool(assessment.explanation.correlated),
        bool(assessment.explanation.neural),
        bool(assessment.explanation.symbolic),
        bool(assessment.explanation.selected),
        bool(assessment.explanation.missing),
        bool(assessment.explanation.uncertainty),
    ]
    selected = next(
        item
        for item in assessment.hypotheses
        if item.hypothesis_id == assessment.selected_hypothesis
    )
    unsupported = 0
    for event_id in selected.supporting_event_ids:
        if event_id not in observed_ids:
            unsupported += 1
    if assessment.explanation.event_ids != assessment.evidence_event_ids:
        unsupported += 1
    provenance = 1.0 if inferred_ok and observed_ok and not invalid else 0.0
    return ExplanationMetrics(
        evidence_reference_validity=0.0 if invalid else 1.0,
        evidence_coverage=round(coverage, 4),
        rule_traceability=0.0 if bad_rules else 1.0,
        explanation_completeness=round(sum(completeness_parts) / len(completeness_parts), 4),
        unsupported_claim_count=unsupported,
        provenance_consistency=provenance,
        inferred_timeline_without_event_id=inferred_ok,
        notes="Synthetic reconstruction metrics. Not a human-rated explanation score.",
    )


def fabricated_event_id_rejected(reconstruction) -> bool:
    fake = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    assessment = assess(reconstruction, window_seconds=300, fingerprint="explain")
    explanation = assessment.explanation
    rebuilt = build_explanation(
        reconstruction,
        assessment.neural,
        assessment.symbolic_hits,
        assessment.hypotheses,
        assessment.selected_hypothesis,
    )
    return fake not in explanation.event_ids and fake not in rebuilt.event_ids
