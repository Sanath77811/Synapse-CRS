"""Controlled robustness checks. Perturbations are synthetic stress tests."""

from __future__ import annotations

from synapse_validation.phase11.flow_loader import FlowRecord
from synapse_validation.phase11.flow_metrics import is_attack, summarize_binary
from synapse_validation.phase11.flow_models import FittedModels, predict_all


def _clone(record: FlowRecord, **changes: object) -> FlowRecord:
    numbers = dict(record.numbers)
    if "numbers" in changes:
        numbers = dict(changes.pop("numbers"))  # type: ignore[arg-type]
    return FlowRecord(
        source_row_id=record.source_row_id,
        source_file=record.source_file,
        line_number=record.line_number,
        fields=record.fields,
        numbers=numbers,
        original_label=record.original_label,
        category=record.category,
        timestamp_raw=record.timestamp_raw,
    )


def run_robustness(
    test: list[FlowRecord],
    models: FittedModels,
) -> dict[str, object]:
    truth = tuple(is_attack(item.category) for item in test)
    baseline = predict_all(models, test)["isolation_forest"]
    noisy = []
    for item in test:
        numbers = dict(item.numbers)
        if "Total Fwd Packets" in numbers:
            numbers["Total Fwd Packets"] = numbers["Total Fwd Packets"] * 1.5
        noisy.append(_clone(item, numbers=numbers))
    noisy_pred = predict_all(models, noisy)["isolation_forest"]
    dropped = []
    for item in test:
        numbers = {key: value for key, value in item.numbers.items() if key != "Destination Port"}
        dropped.append(_clone(item, numbers=numbers))
    dropped_pred = predict_all(models, dropped)["isolation_forest"]
    unseen = sum(1 for item in test if item.category == "benchmark_unlabelled")
    unsupported = [
        item.original_label
        for item in test
        if item.category not in {"benchmark_benign_flow", "benchmark_attack_labelled_flow"}
    ]
    return {
        "baseline_isolation_forest": summarize_binary(truth, baseline["pred"], baseline["scores"]),
        "noisy_fwd_packets_times_1_5": summarize_binary(
            truth, noisy_pred["pred"], noisy_pred["scores"]
        ),
        "missing_destination_port_median_impute": summarize_binary(
            truth, dropped_pred["pred"], dropped_pred["scores"]
        ),
        "unlabelled_rows_in_test": unseen,
        "unsupported_original_labels": unsupported,
        "perturbations": "synthetic stress tests on the evaluation records; not live traffic",
        "open_set_policy": (
            "Unknown/unlabelled rows are not mapped to BENIGN. They remain non-benign "
            "for binary scoring and are listed explicitly."
        ),
    }
