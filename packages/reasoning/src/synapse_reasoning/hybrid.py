"""Combine reconstruction quality, neural scores, and symbolic hits."""

from uuid import UUID, uuid4

from synapse_reasoning import ENGINE_VERSION
from synapse_reasoning.explanation import build_explanation
from synapse_reasoning.features import extract_features
from synapse_reasoning.models import (
    HypothesisId,
    HypothesisRecord,
    ReasoningAssessment,
    Reconstruction,
)
from synapse_reasoning.neural import score_features
from synapse_reasoning.prediction import predict_event_volume
from synapse_reasoning.symbolic import evaluate_rules

HYPOTHESES: tuple[HypothesisId, ...] = (
    "H1_normal",
    "H2_unusual_legitimate",
    "H3_suspicious_pattern",
    "H4_insufficient_evidence",
)


def assess(
    reconstruction: Reconstruction,
    *,
    window_seconds: int,
    fingerprint: str,
) -> ReasoningAssessment:
    features = extract_features(reconstruction, window_seconds=window_seconds)
    neural = score_features(features)
    hits = evaluate_rules(reconstruction, features)
    hypotheses = _hypotheses(reconstruction, neural, hits)
    selected = _select(hypotheses)
    explanation = build_explanation(reconstruction, neural, hits, hypotheses, selected)
    prediction = predict_event_volume(reconstruction, features)
    confidence = next(item.support for item in hypotheses if item.hypothesis_id == selected)
    if selected == "H3_suspicious_pattern":
        severity = "medium"
    elif selected == "H4_insufficient_evidence":
        severity = "low"
    else:
        severity = "info"
    return ReasoningAssessment(
        assessment_id=uuid4(),
        target_id=reconstruction.target_id,
        reconstruction_id=reconstruction.reconstruction_id,
        created_at=reconstruction.created_at,
        engine_version=ENGINE_VERSION,
        dataset_label=reconstruction.dataset_label,
        evidence_event_ids=reconstruction.supporting_event_ids,
        finding_types=tuple(sorted({item.finding_type for item in reconstruction.findings})),
        quality=reconstruction.quality,
        neural=neural,
        symbolic_hits=hits,
        hypotheses=hypotheses,
        selected_hypothesis=selected,
        explanation=explanation,
        prediction=prediction,
        counterfactual=None,
        proposal=None,
        verification=None,
        confidence=round(confidence, 4),
        severity=severity,
        uncertainty=explanation.uncertainty,
        missing_evidence=reconstruction.missing_evidence,
        limitations=(
            "Hybrid foundation on synthetic-trained Isolation Forest plus inspectable rules.",
            "Not a complete autonomous cyber reasoning system.",
            "Phase 8 risk scores are not reused as attack probabilities.",
        ),
        fingerprint=fingerprint,
        features=features,
    )


def _hypotheses(reconstruction, neural, hits) -> tuple[HypothesisRecord, ...]:
    support: dict[HypothesisId, float] = {item: 0.0 for item in HYPOTHESES}
    events: dict[HypothesisId, list[UUID]] = {item: [] for item in HYPOTHESES}
    rules: dict[HypothesisId, list[str]] = {item: [] for item in HYPOTHESES}
    missing: dict[HypothesisId, list[str]] = {item: [] for item in HYPOTHESES}
    for hit in hits:
        support[hit.hypothesis] = max(support[hit.hypothesis], hit.support)
        events[hit.hypothesis].extend(hit.evidence_event_ids)
        rules[hit.hypothesis].append(hit.rule_id)
        missing[hit.hypothesis].extend(hit.missing)
    if neural.unusual:
        support["H3_suspicious_pattern"] = max(support["H3_suspicious_pattern"], 0.6)
        support["H2_unusual_legitimate"] = max(support["H2_unusual_legitimate"], 0.5)
    else:
        support["H1_normal"] = max(support["H1_normal"], 0.65)
    if (
        reconstruction.quality.reconstruction_completeness < 0.4
        or len(reconstruction.observations) < 2
    ):
        support["H4_insufficient_evidence"] = max(support["H4_insufficient_evidence"], 0.85)
        support["H3_suspicious_pattern"] = min(support["H3_suspicious_pattern"], 0.4)
    records = []
    selected = _select_id(support)
    for hyp in HYPOTHESES:
        if hyp == selected:
            status = "selected"
        elif support[hyp] >= 0.5:
            status = "viable"
        else:
            status = "rejected"
        records.append(
            HypothesisRecord(
                hypothesis_id=hyp,
                support=round(support[hyp], 4),
                supporting_event_ids=tuple(dict.fromkeys(events[hyp])),
                contradicting=_contradict(hyp, neural, reconstruction),
                missing_evidence=tuple(dict.fromkeys(missing[hyp])),
                rules=tuple(rules[hyp]),
                neural_signal=(
                    f"unusualness={neural.unusualness_score} threshold={neural.threshold}"
                ),
                assumptions=(
                    "Enrolled telemetry only",
                    "Synthetic Isolation Forest baseline",
                ),
                rationale=_rationale(hyp, support[hyp], neural, reconstruction),
                status=status,  # type: ignore[arg-type]
            )
        )
    return tuple(records)


def _select_id(support: dict[HypothesisId, float]) -> HypothesisId:
    # Conservative: insufficient evidence wins ties against H3.
    ranked = sorted(support.items(), key=lambda item: item[1], reverse=True)
    best_score = ranked[0][1]
    tied = [name for name, score in ranked if score == best_score]
    if "H4_insufficient_evidence" in tied:
        return "H4_insufficient_evidence"
    if "H1_normal" in tied:
        return "H1_normal"
    return ranked[0][0]


def _select(records: tuple[HypothesisRecord, ...]) -> HypothesisId:
    return next(item.hypothesis_id for item in records if item.status == "selected")


def _contradict(hyp, neural, reconstruction) -> tuple[str, ...]:
    notes = []
    if hyp == "H1_normal" and neural.unusual:
        notes.append("neural unusualness at or above threshold")
    if hyp == "H3_suspicious_pattern" and not reconstruction.findings and not neural.unusual:
        notes.append("no Phase 8 findings and neural score below threshold")
    if hyp == "H1_normal" and reconstruction.missing_evidence:
        notes.append("missing process evidence")
    return tuple(notes)


def _rationale(hyp, support, neural, reconstruction) -> str:
    if hyp == "H4_insufficient_evidence":
        return "Sparse or ambiguous evidence is treated as insufficient, not malicious."
    if hyp == "H1_normal":
        return "Complete or low-volume behaviour without unusual neural score."
    if hyp == "H2_unusual_legitimate":
        return "Findings or unusualness exist, but intent is not established."
    return (
        f"Pattern hypothesis support={support} with neural unusual={neural.unusual} "
        f"and {len(reconstruction.findings)} Phase 8 findings."
    )
