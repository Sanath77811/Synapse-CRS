"""Synthetic evaluation of the Isolation Forest versus Phase 8 findings."""

import json
from dataclasses import dataclass

from synapse_reasoning.features import FEATURE_DEFINITIONS, FeatureVector
from synapse_reasoning.neural import DATA_PATH, score_features


@dataclass(frozen=True)
class EvalReport:
    dataset: str
    train_rows: int
    test_normal: int
    test_unusual: int
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    notes: str


def evaluate_neural_holdout() -> EvalReport:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    rows = payload["rows"]
    train_count = int(payload.get("train_count", 30))
    typical = rows[:40]
    unusual = rows[40:]
    test_typical = typical[train_count:40]
    test_unusual = unusual
    names = list(FEATURE_DEFINITIONS)

    def as_vector(row: dict) -> FeatureVector:
        return FeatureVector(
            version="1.0.0",
            values={name: float(row[name]) for name in names},
            sources={name: "synthetic" for name in names},
            window_seconds=300,
        )

    false_pos = 0
    true_pos = 0
    false_neg = 0
    true_neg = 0
    for row in test_typical:
        unusual_flag = score_features(as_vector(row)).unusual
        if unusual_flag:
            false_pos += 1
        else:
            true_neg += 1
    for row in test_unusual:
        unusual_flag = score_features(as_vector(row)).unusual
        if unusual_flag:
            true_pos += 1
        else:
            false_neg += 1
    precision = true_pos / max(true_pos + false_pos, 1)
    recall = true_pos / max(true_pos + false_neg, 1)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    fpr = false_pos / max(false_pos + true_neg, 1)
    return EvalReport(
        dataset="synthetic_lab_features_v1",
        train_rows=40,
        test_normal=len(test_typical),
        test_unusual=len(test_unusual),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        false_positive_rate=round(fpr, 4),
        notes=(
            "Holdout is synthetic and tiny. Metrics are not enterprise detection rates. "
            "The forest is fitted on the first 30 typical rows only."
        ),
    )
