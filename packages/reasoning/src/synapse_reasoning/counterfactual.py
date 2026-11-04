"""Feature ablation and rule sensitivity. Not causal identification."""

from uuid import uuid4

from synapse_correlation.models import Finding, Observation

from synapse_reasoning.hybrid import assess
from synapse_reasoning.models import Counterfactual, ReasoningAssessment, Reconstruction
from synapse_reasoning.reconstruction import reconstruct


def ablate_repeated_network(
    reconstruction: Reconstruction,
    baseline: ReasoningAssessment,
) -> Counterfactual:
    """Drop network observations after the first two per process identity."""
    allowed: dict[str, int] = {}
    kept: list[Observation] = []
    from synapse_correlation.identity import covering_identities, index_process_events

    started, exited, _ = index_process_events(reconstruction.observations)
    for item in reconstruction.observations:
        if item.event_type != "network_connection_observed":
            kept.append(item)
            continue
        matches = covering_identities(item, started, exited)
        key = matches[0].key() if len(matches) == 1 else "unbound"
        allowed[key] = allowed.get(key, 0) + 1
        if allowed[key] <= 2:
            kept.append(item)
    findings = tuple(
        item
        for item in reconstruction.findings
        if item.finding_type not in {"repeated_network_activity", "multi_port_network_activity"}
    )
    rebuilt = reconstruct(
        tuple(kept),
        findings,
        reconstruction.links,
        created_at=reconstruction.created_at,
        dataset_label=reconstruction.dataset_label,
    )
    alt = assess(rebuilt, window_seconds=300, fingerprint="counterfactual")
    changed = []
    for name, value in baseline.features.values.items():
        if alt.features.values.get(name) != value:
            changed.append(name)
    unchanged = [name for name in baseline.features.values if name not in changed]
    return Counterfactual(
        counterfactual_id=uuid4(),
        baseline_assessment_id=baseline.assessment_id,
        description="Keep at most two covering network observations per process identity.",
        modified_assumptions=("repeated network volume removed",),
        changed_features=tuple(changed),
        unchanged_features=tuple(unchanged),
        baseline_hypothesis=baseline.selected_hypothesis,
        result_hypothesis=alt.selected_hypothesis,
        baseline_unusual=baseline.neural.unusual,
        result_unusual=alt.neural.unusual,
        difference=(
            f"hypothesis {baseline.selected_hypothesis} -> {alt.selected_hypothesis}; "
            f"unusual {baseline.neural.unusual} -> {alt.neural.unusual}"
        ),
        limitations=(
            "Feature ablation, not a causal intervention on a host. "
            "Stored telemetry was not modified."
        ),
        kind="feature_ablation",
    )


def drop_finding_type(
    reconstruction: Reconstruction,
    baseline: ReasoningAssessment,
    finding_type: str,
) -> Counterfactual:
    findings: tuple[Finding, ...] = tuple(
        item for item in reconstruction.findings if item.finding_type != finding_type
    )
    rebuilt = reconstruct(
        reconstruction.observations,
        findings,
        reconstruction.links,
        created_at=reconstruction.created_at,
        dataset_label=reconstruction.dataset_label,
    )
    alt = assess(rebuilt, window_seconds=300, fingerprint="counterfactual-rule")
    return Counterfactual(
        counterfactual_id=uuid4(),
        baseline_assessment_id=baseline.assessment_id,
        description=f"Rule sensitivity: omit {finding_type} findings.",
        modified_assumptions=(f"no {finding_type}",),
        changed_features=(),
        unchanged_features=tuple(baseline.features.values),
        baseline_hypothesis=baseline.selected_hypothesis,
        result_hypothesis=alt.selected_hypothesis,
        baseline_unusual=baseline.neural.unusual,
        result_unusual=alt.neural.unusual,
        difference=(f"hypothesis {baseline.selected_hypothesis} -> {alt.selected_hypothesis}"),
        limitations="Symbolic sensitivity only; neural features still see the events.",
        kind="rule_sensitivity",
    )


def feature_contributions(baseline: ReasoningAssessment) -> tuple[str, ...]:
    return tuple(f"{name}:{delta}" for name, delta in baseline.neural.feature_contributions)
