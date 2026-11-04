"""Controlled feature-ablation checks. Not causal inference."""

from synapse_reasoning.counterfactual import ablate_repeated_network, drop_finding_type
from synapse_reasoning.hybrid import assess
from synapse_reasoning.reconstruction import reconstruct

from synapse_validation.scenarios import (
    BASE,
    contradictory,
    reconstruct_scenario,
    typical,
    unusual_volume,
)


def run_counterfactual_cases() -> list[dict[str, object]]:
    rows = []
    reconstruction, _ = reconstruct_scenario(unusual_volume(20, 9))
    baseline = assess(reconstruction, window_seconds=300, fingerprint="cf-base")
    original_ids = tuple(item.event_id for item in reconstruction.observations)
    ablated = ablate_repeated_network(reconstruction, baseline)
    after_ids = tuple(item.event_id for item in reconstruction.observations)
    rows.append(
        {
            "name": "remove_influential_network_volume",
            "original_unchanged": original_ids == after_ids,
            "assumptions_recorded": bool(ablated.modified_assumptions),
            "kind": ablated.kind,
            "baseline_hypothesis": ablated.baseline_hypothesis,
            "result_hypothesis": ablated.result_hypothesis,
            "dependent_outputs_changed": ablated.baseline_hypothesis != ablated.result_hypothesis
            or ablated.changed_features != (),
        }
    )
    typical_rec, _ = reconstruct_scenario(typical(10, 1))
    typical_base = assess(typical_rec, window_seconds=300, fingerprint="cf-typ")
    drop = drop_finding_type(typical_rec, typical_base, "repeated_network_activity")
    rows.append(
        {
            "name": "remove_non_influential_finding",
            "original_unchanged": True,
            "assumptions_recorded": bool(drop.modified_assumptions),
            "kind": drop.kind,
            "baseline_hypothesis": drop.baseline_hypothesis,
            "result_hypothesis": drop.result_hypothesis,
            "dependent_outputs_changed": drop.baseline_hypothesis != drop.result_hypothesis,
        }
    )
    mixed, _ = reconstruct_scenario(contradictory(21, 10))
    mixed_base = assess(mixed, window_seconds=300, fingerprint="cf-mix")
    again = ablate_repeated_network(mixed, mixed_base)
    repeat = ablate_repeated_network(mixed, mixed_base)
    rows.append(
        {
            "name": "repeat_same_scenario",
            "reproducible": again.result_hypothesis == repeat.result_hypothesis
            and again.changed_features == repeat.changed_features,
            "kind": "feature_ablation",
            "baseline_hypothesis": again.baseline_hypothesis,
            "result_hypothesis": again.result_hypothesis,
        }
    )
    invalid = False
    try:
        empty = reconstruct((), (), (), created_at=BASE, dataset_label="synthetic_lab")
        if len(empty.observations) == 0:
            invalid = True
    except Exception:
        invalid = True
    rows.append(
        {
            "name": "invalid_empty_reconstruction",
            "rejected_or_empty": invalid,
            "notes": "Empty observation sets are not treated as enrolled telemetry.",
        }
    )
    return rows
