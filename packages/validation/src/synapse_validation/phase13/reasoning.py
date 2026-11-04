"""Completeness-aware sample hypotheses. Not Phase 9 Linux hybrid."""

from __future__ import annotations

from sklearn.ensemble import IsolationForest

from synapse_validation.metrics import binary_confusion
from synapse_validation.phase12.splits import SampleSplit, _sample_label
from synapse_validation.phase13.features import SampleFeatureRow

METHOD_ID = "completeness_aware_union_v1"
FEATURE_ORDER = (
    "event_count",
    "process_count",
    "orphan_count",
    "incomplete_lifecycle_count",
    "parent_edge_count",
    "network_ref_count",
    "completeness_ratio",
    "pid_reuse_flag",
)


def _majority(labels: list[str]) -> str:
    return "malicious" if labels.count("malicious") > labels.count("benign") else "benign"


def fit_thresholds(train_rows: list[SampleFeatureRow], train_labels: list[str]) -> dict[str, float]:
    benign_process = [
        row.values["process_count"]
        for row, label in zip(train_rows, train_labels, strict=True)
        if label == "benign"
    ]
    if benign_process:
        idx = int(0.95 * max(len(benign_process) - 1, 0))
        volume = sorted(benign_process)[idx]
    else:
        volume = 10.0
    return {"volume": volume, "completeness_min": 0.4}


def predict_row(row: SampleFeatureRow, thresholds: dict[str, float]) -> dict[str, object]:
    values = row.values
    symbolic = values["orphan_count"] >= 1 or values["incomplete_lifecycle_count"] >= 2
    volume = values["process_count"] > thresholds["volume"]
    low_evidence = (
        values["completeness_ratio"] < thresholds["completeness_min"]
        and values["process_count"] <= 1
    )
    if low_evidence and not symbolic:
        decision = "insufficient"
    elif symbolic or volume:
        decision = "malicious"
    else:
        decision = "benign"
    return {
        "decision": decision,
        "symbolic": symbolic,
        "volume": volume,
        "low_evidence": low_evidence,
        "abstain": decision == "insufficient",
    }


def evaluate(
    features: dict[str, SampleFeatureRow],
    grouped_labels: dict[str, str],
    split: SampleSplit,
) -> dict[str, object]:
    train_ids = [sid for sid in split.train_samples if sid in features]
    train_rows = [features[sid] for sid in train_ids]
    train_labels = [grouped_labels.get(sid, "unknown") for sid in train_ids]
    thresholds = fit_thresholds(train_rows, train_labels)
    majority = _majority([label for label in train_labels if label in {"benign", "malicious"}])
    test_ids = [sid for sid in split.test_samples if sid in features]
    truth = tuple(grouped_labels.get(sid) == "malicious" for sid in test_ids)

    def pack(name: str, pred: tuple[bool, ...]) -> dict[str, object]:
        confusion = binary_confusion(truth, pred)
        return {
            "true_positive": confusion.true_positive,
            "false_positive": confusion.false_positive,
            "true_negative": confusion.true_negative,
            "false_negative": confusion.false_negative,
            "precision": confusion.precision,
            "recall": confusion.recall,
            "f1": confusion.f1,
            "false_positive_rate": confusion.false_positive_rate,
            "accuracy": confusion.accuracy,
            "evaluation_unit": "sample",
            "method": name,
        }

    majority_pred = tuple(majority == "malicious" for _ in test_ids)
    symbolic_pred = tuple(
        bool(predict_row(features[sid], thresholds)["symbolic"]) for sid in test_ids
    )
    volume_pred = tuple(bool(predict_row(features[sid], thresholds)["volume"]) for sid in test_ids)
    union_pred = tuple(s or v for s, v in zip(symbolic_pred, volume_pred, strict=True))
    aware = [predict_row(features[sid], thresholds) for sid in test_ids]
    aware_pred = tuple(item["decision"] == "malicious" for item in aware)
    abstain = sum(1 for item in aware if item["abstain"])
    forest = None
    forest_threshold = 0.0
    benign_rows = [
        [features[sid].values[name] for name in FEATURE_ORDER]
        for sid in train_ids
        if grouped_labels.get(sid) == "benign"
    ]
    if len(benign_rows) >= 2:
        forest = IsolationForest(
            n_estimators=40,
            max_samples=min(32, len(benign_rows)),
            random_state=42,
            n_jobs=1,
        )
        forest.fit(benign_rows)
        scores = sorted(-float(forest.decision_function([row])[0]) for row in benign_rows)
        forest_threshold = scores[min(len(scores) - 1, int(0.9 * (len(scores) - 1)))]

    def isolation(sid: str) -> bool:
        if forest is None:
            return False
        row = [features[sid].values[name] for name in FEATURE_ORDER]
        return -float(forest.decision_function([row])[0]) >= forest_threshold

    isolation_pred = tuple(isolation(sid) for sid in test_ids)
    hybrid_pred = tuple(a or i for a, i in zip(aware_pred, isolation_pred, strict=True))
    return {
        "method_family": METHOD_ID,
        "not_phase9_hybrid": True,
        "thresholds_fit_on": "train samples only",
        "thresholds": thresholds,
        "majority": pack("majority", majority_pred),
        "volume_rule": pack("volume_rule", volume_pred),
        "symbolic": pack("symbolic", symbolic_pred),
        "union": pack("union", union_pred),
        "ml_isolation_forest": pack("ml_isolation_forest", isolation_pred),
        "completeness_aware": pack(METHOD_ID, aware_pred),
        "completeness_aware_or_if": pack("completeness_aware_or_if_v1", hybrid_pred),
        "forest_fitted": forest is not None,
        "abstain_count": abstain,
        "test_n": len(test_ids),
        "phase9_hybrid": {
            "status": "not_comparable",
            "reason": "Linux identity model is not used for DMBD/Wintap rows.",
        },
        "hypothesis": (
            "Abstaining when completeness is low reduces confident errors versus union, "
            "at the cost of recall. Isolation Forest is a separate ML-only baseline."
        ),
        "ablation_completeness_min_zero": pack(
            "union_as_completeness_disabled",
            union_pred,
        ),
    }


def labels_by_sample(records) -> dict[str, str]:
    from collections import defaultdict

    grouped: dict[str, list] = defaultdict(list)
    for item in records:
        grouped[item.source_sample_id].append(item)
    return {sid: _sample_label(rows) for sid, rows in grouped.items()}
