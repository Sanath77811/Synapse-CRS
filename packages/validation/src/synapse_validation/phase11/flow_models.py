"""Flow baselines. Phase 9 hybrid is not comparable on these inputs."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.ensemble import IsolationForest

from synapse_validation.phase11.flow_loader import FlowRecord
from synapse_validation.phase11.flow_metrics import is_attack

FEATURE_ORDER = (
    "Destination Port",
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
)


def _vector(record: FlowRecord, medians: dict[str, float]) -> list[float]:
    return [record.numbers.get(name, medians[name]) for name in FEATURE_ORDER]


def _medians(records: list[FlowRecord]) -> dict[str, float]:
    medians: dict[str, float] = {}
    for name in FEATURE_ORDER:
        values = sorted(item.numbers[name] for item in records if name in item.numbers)
        if not values:
            medians[name] = 0.0
            continue
        medians[name] = values[len(values) // 2]
    return medians


def _packets(record: FlowRecord, medians: dict[str, float]) -> float:
    fwd = record.numbers.get("Total Fwd Packets", medians["Total Fwd Packets"])
    bwd = record.numbers.get("Total Backward Packets", medians["Total Backward Packets"])
    return fwd + bwd


@dataclass
class FittedModels:
    majority_label: str
    majority_is_attack: bool
    packet_threshold: float
    medians: dict[str, float]
    forest: IsolationForest
    forest_threshold: float
    contamination: float
    notes: dict[str, str]


def fit_models(
    train: list[FlowRecord],
    validation: list[FlowRecord],
) -> FittedModels:
    if not train:
        raise ValueError("empty train")
    medians = _medians(train)
    attack_n = sum(1 for item in train if is_attack(item.category))
    majority = (
        "benchmark_attack_labelled_flow" if attack_n > len(train) / 2 else "benchmark_benign_flow"
    )
    benign = [item for item in train if not is_attack(item.category)]
    packet_values = sorted(_packets(item, medians) for item in benign) or [0.0]
    packet_threshold = packet_values[min(len(packet_values) - 1, int(0.95 * len(packet_values)))]
    contamination = min(0.5, max(0.01, attack_n / max(len(train), 1)))
    population = benign or train
    rows = [_vector(item, medians) for item in population]
    forest = IsolationForest(
        n_estimators=80,
        max_samples=min(256, len(rows)),
        contamination="auto",
        random_state=42,
        n_jobs=1,
    )
    forest.fit(rows)
    val_scores = []
    val_labels = []
    for item in validation:
        score = -float(forest.decision_function([_vector(item, medians)])[0])
        val_scores.append(score)
        val_labels.append(is_attack(item.category))
    if val_scores and any(val_labels) and not all(val_labels):
        candidates = sorted(set(val_scores))
        best_t = candidates[0]
        best_f1 = -1.0
        for threshold in candidates:
            pred = tuple(score >= threshold for score in val_scores)
            tp = sum(1 for flag, label in zip(pred, val_labels, strict=True) if flag and label)
            fp = sum(1 for flag, label in zip(pred, val_labels, strict=True) if flag and not label)
            fn = sum(1 for flag, label in zip(pred, val_labels, strict=True) if not flag and label)
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
            if f1 > best_f1:
                best_f1 = f1
                best_t = threshold
        forest_threshold = best_t
        thresh_note = "Isolation Forest threshold maximises F1 on validation only."
    else:
        train_scores = sorted(
            -float(forest.decision_function([_vector(item, medians)])[0]) for item in population
        )
        forest_threshold = train_scores[min(len(train_scores) - 1, int(0.95 * len(train_scores)))]
        thresh_note = (
            "Validation lacked both classes; threshold is the 95th percentile of "
            "train-population unusualness."
        )
    return FittedModels(
        majority_label=majority,
        majority_is_attack=majority == "benchmark_attack_labelled_flow",
        packet_threshold=packet_threshold,
        medians=medians,
        forest=forest,
        forest_threshold=forest_threshold,
        contamination=contamination,
        notes={
            "majority": "Predict the training majority category. Assumes stationarity.",
            "volume_rule": (
                "Attack if fwd+bwd packets exceed the 95th percentile of training BENIGN "
                "packet totals. Fitted on train only."
            ),
            "isolation_forest": (
                "Fitted on training BENIGN rows when available. unusualness=-decision_function, "
                "not a probability. " + thresh_note
            ),
            "flow_union": (
                "Attack if the volume rule or Isolation Forest fires. This is a new flow-level "
                "ensemble, not the Phase 9 process hybrid."
            ),
            "phase9_hybrid": "not comparable: requires process reconstructions, not flows.",
        },
    )


def predict_all(models: FittedModels, records: list[FlowRecord]) -> dict[str, dict[str, object]]:
    majority_pred = []
    rule_pred = []
    forest_pred = []
    union_pred = []
    forest_scores = []
    rule_scores = []
    for item in records:
        packets = _packets(item, models.medians)
        rule = packets > models.packet_threshold
        score = -float(models.forest.decision_function([_vector(item, models.medians)])[0])
        forest = score >= models.forest_threshold
        majority_pred.append(models.majority_is_attack)
        rule_pred.append(rule)
        forest_pred.append(forest)
        union_pred.append(rule or forest)
        forest_scores.append(score)
        rule_scores.append(packets)
    return {
        "majority": {"pred": tuple(majority_pred), "scores": None},
        "volume_rule": {"pred": tuple(rule_pred), "scores": tuple(rule_scores)},
        "isolation_forest": {"pred": tuple(forest_pred), "scores": tuple(forest_scores)},
        "flow_union": {"pred": tuple(union_pred), "scores": tuple(forest_scores)},
    }
