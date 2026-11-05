"""Sample-level detection only. Isolation Forest scores are not probabilities."""

from __future__ import annotations

from collections import defaultdict

from sklearn.ensemble import IsolationForest

from synapse_validation.metrics import binary_confusion
from synapse_validation.phase12.reconstruction import ProcessNode, reconstruct
from synapse_validation.phase12.records import EndpointRecord
from synapse_validation.phase12.splits import SampleSplit, _sample_label


def _sample_features(
    records: tuple[EndpointRecord, ...], nodes: tuple[ProcessNode, ...]
) -> dict[str, list[float]]:
    by_sample: dict[str, list[EndpointRecord]] = defaultdict(list)
    for item in records:
        by_sample[item.source_sample_id].append(item)
    nodes_by_sample: dict[str, list[ProcessNode]] = defaultdict(list)
    for node in nodes:
        nodes_by_sample[node.sample_id].append(node)
    features: dict[str, list[float]] = {}
    for sid, rows in by_sample.items():
        group = nodes_by_sample.get(sid, [])
        features[sid] = [
            float(len(rows)),
            float(len(group)),
            float(sum(1 for item in group if item.orphan)),
            float(sum(1 for item in group if not item.complete)),
            float(sum(1 for item in group if item.parent_identity)),
        ]
    return features


def _majority(labels: list[str]) -> str:
    if labels.count("malicious") > labels.count("benign"):
        return "malicious"
    return "benign"


def evaluate_sample_detection(
    records: tuple[EndpointRecord, ...],
    split: SampleSplit,
) -> dict[str, object]:
    reconstruction = reconstruct(records)
    features = _sample_features(records, reconstruction.nodes)
    grouped: dict[str, list[EndpointRecord]] = defaultdict(list)
    for item in records:
        grouped[item.source_sample_id].append(item)

    def labels_for(ids: tuple[str, ...]) -> list[str]:
        return [_sample_label(grouped[sid]) for sid in ids]

    train_y = labels_for(split.train_samples)
    majority = _majority(train_y)
    benign_children = [
        features[sid][1] for sid in split.train_samples if _sample_label(grouped[sid]) == "benign"
    ]
    if benign_children:
        idx = int(0.95 * max(len(benign_children) - 1, 0))
        threshold = sorted(benign_children)[idx]
    else:
        threshold = 10
    train_rows = [
        features[sid] for sid in split.train_samples if _sample_label(grouped[sid]) == "benign"
    ]
    forest = None
    forest_threshold = 0.0
    if len(train_rows) >= 2:
        forest = IsolationForest(
            n_estimators=40,
            max_samples=min(32, len(train_rows)),
            random_state=42,
            n_jobs=1,
        )
        forest.fit(train_rows)
        scores = sorted(-float(forest.decision_function([row])[0]) for row in train_rows)
        forest_threshold = scores[min(len(scores) - 1, int(0.9 * (len(scores) - 1)))]

    def predict(sid: str) -> dict[str, bool]:
        row = features[sid]
        symbolic = row[2] >= 1 or row[3] >= 2
        volume = row[1] > threshold
        unusual = False
        if forest is not None:
            unusual = -float(forest.decision_function([row])[0]) >= forest_threshold
        return {
            "majority": majority == "malicious",
            "child_count_rule": volume,
            "symbolic_incomplete_or_orphan": symbolic,
            "isolation_forest": unusual,
            "endpoint_union": volume or symbolic,
        }

    test_ids = split.test_samples
    truth = tuple(label == "malicious" for label in labels_for(test_ids))
    methods = {}
    for name in (
        "majority",
        "child_count_rule",
        "symbolic_incomplete_or_orphan",
        "isolation_forest",
        "endpoint_union",
    ):
        pred = tuple(predict(sid)[name] for sid in test_ids)
        confusion = binary_confusion(truth, pred)
        methods[name] = {
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
        }
    methods["phase9_hybrid"] = {
        "status": "not_comparable",
        "reason": (
            "Phase 9 requires Linux observations with agent_id, boot_id, pid, and "
            "start_ticks. DMBD/Wintap pid_hash must not be rewritten into that model."
        ),
    }
    return {
        "label_scope": "sample",
        "methods": methods,
        "child_count_threshold": threshold,
        "forest_fitted": forest is not None,
        "test_support": dict(split.test_labels),
        "notes": (
            "Positive class is sample label malicious. Event-level accuracy is not reported."
        ),
    }
