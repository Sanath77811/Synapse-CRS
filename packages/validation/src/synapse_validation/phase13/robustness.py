"""Synthetic perturbations. Separate from independent-dataset experiments."""

from __future__ import annotations

from synapse_validation.phase12.records import EndpointRecord, unavailable
from synapse_validation.phase12.robustness import run_robustness as phase12_robustness
from synapse_validation.phase13.explanations import evaluate_explanations
from synapse_validation.phase13.features import extract_sample_features
from synapse_validation.phase13.reasoning import fit_thresholds, labels_by_sample
from synapse_validation.phase13.reconstruction import annotate


def _replace(record: EndpointRecord, **changes: object) -> EndpointRecord:
    data = record.__dict__.copy()
    data.update(changes)
    return EndpointRecord(**data)


def run_robustness(records: tuple[EndpointRecord, ...]) -> dict[str, object]:
    baseline = annotate(records)
    duplicated = records + records[:1] if records else records
    truncated = records[: max(1, len(records) // 2)] if records else records
    conflicting = records
    if records:
        first = records[0]
        conflicting = records + (
            _replace(
                first,
                source_record_id=first.source_record_id + ":conflict",
                source_parent_process_id=type(first.source_parent_process_id)(
                    value="other-parent",
                    provenance="observed",
                ),
            ),
        )
    nodes = baseline["base"].nodes
    features = extract_sample_features(records, nodes)
    labels = labels_by_sample(records)
    train_rows = list(features.values())
    train_labels = [labels.get(row.sample_id, "unknown") for row in train_rows]
    thresholds = fit_thresholds(train_rows, train_labels)
    explanations = evaluate_explanations(records, nodes, features, thresholds)
    return {
        "kind": "synthetic_perturbation",
        "not_independent_dataset": True,
        "phase12": phase12_robustness(records),
        "duplicate_records_process_count": annotate(duplicated)["process_count"],
        "window_truncation_process_count": annotate(truncated)["process_count"],
        "conflicting_parent_contradictions": sum(
            1 for node in annotate(conflicting)["nodes"] if node.contradictions
        ),
        "missing_creation": annotate(
            tuple(
                item
                for item in records
                if item.event_type not in {"process_create", "process_started"}
            )
        )["process_count"],
        "parents_unavailable_unsupported": annotate(
            tuple(_replace(item, source_parent_process_id=unavailable()) for item in records)
        )["relationship_counts"]["unsupported"],
        "explanation_after_baseline": {
            "unsupported_claim_count": explanations["unsupported_claim_count"],
            "stability_compared": explanations["stability_compared"],
        },
    }
