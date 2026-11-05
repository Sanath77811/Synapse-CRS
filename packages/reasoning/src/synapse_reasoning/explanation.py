"""Structured analyst-facing explanation. Natural language is not the source of truth."""

from synapse_reasoning.models import Explanation, HypothesisId, Reconstruction


def build_explanation(
    reconstruction: Reconstruction,
    neural,
    hits,
    hypotheses,
    selected: HypothesisId,
) -> Explanation:
    selected_row = next(item for item in hypotheses if item.hypothesis_id == selected)
    observed_types = sorted({item.event_type for item in reconstruction.observations})
    finding_types = sorted({item.finding_type for item in reconstruction.findings})
    event_ids = reconstruction.supporting_event_ids
    rule_ids = tuple(hit.rule_id for hit in hits)
    contradiction = "; ".join(selected_row.contradicting) or "none recorded"
    missing = "; ".join(reconstruction.missing_evidence) or "none recorded"
    return Explanation(
        summary=(
            f"Selected {selected} (support={selected_row.support}). "
            "This is a hybrid research assessment, not a compromise verdict."
        ),
        observed=f"Observed event types: {observed_types or 'none'}.",
        correlated=f"Phase 8 finding types: {finding_types or 'none'}.",
        neural=(
            f"Isolation Forest unusualness={neural.unusualness_score} "
            f"threshold={neural.threshold} unusual={neural.unusual}."
        ),
        symbolic="; ".join(f"{hit.rule_id}->{hit.hypothesis}" for hit in hits) or "no rules fired",
        hypotheses="; ".join(
            f"{item.hypothesis_id}:{item.support}:{item.status}" for item in hypotheses
        ),
        selected=f"{selected}: {selected_row.rationale}",
        support=f"event_ids={list(selected_row.supporting_event_ids)[:8]}",
        contradiction=contradiction,
        missing=missing,
        uncertainty=(
            "Neural scores are not probabilities. Reconstruction completeness "
            f"={reconstruction.quality.reconstruction_completeness} is not attack confidence."
        ),
        event_ids=event_ids,
        rule_ids=rule_ids,
    )
