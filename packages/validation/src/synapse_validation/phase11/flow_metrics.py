"""Flow-task metrics. Binary malicious = not BENIGN category."""

from __future__ import annotations

import math
from collections import Counter

from synapse_validation.metrics import _safe_div, binary_confusion


def is_attack(category: str) -> bool:
    return category != "benchmark_benign_flow"


def bootstrap_f1(
    y_true: tuple[bool, ...],
    y_pred: tuple[bool, ...],
    *,
    seed: int = 42,
    rounds: int = 200,
) -> dict[str, float]:
    if not y_true:
        return {"f1_mean": 0.0, "f1_lo": 0.0, "f1_hi": 0.0, "rounds": 0}
    state = seed
    scores: list[float] = []
    n = len(y_true)
    for _ in range(rounds):
        sample_true: list[bool] = []
        sample_pred: list[bool] = []
        for _index in range(n):
            state = (1103515245 * state + 12345) % (2**31)
            pick = state % n
            sample_true.append(y_true[pick])
            sample_pred.append(y_pred[pick])
        scores.append(binary_confusion(tuple(sample_true), tuple(sample_pred)).f1)
    scores.sort()
    lo = scores[int(0.025 * (len(scores) - 1))]
    hi = scores[int(0.975 * (len(scores) - 1))]
    mean = sum(scores) / len(scores)
    return {
        "f1_mean": round(mean, 4),
        "f1_lo": round(lo, 4),
        "f1_hi": round(hi, 4),
        "rounds": rounds,
        "method": "percentile bootstrap of test predictions; not a significance test",
    }


def per_class_scores(
    y_true: tuple[str, ...], y_pred: tuple[str, ...]
) -> dict[str, dict[str, float]]:
    labels = tuple(sorted(set(y_true) | set(y_pred)))
    result: dict[str, dict[str, float]] = {}
    for label in labels:
        pairs = list(zip(y_true, y_pred, strict=True))
        tp = sum(1 for truth, pred in pairs if truth == label and pred == label)
        fp = sum(1 for truth, pred in pairs if truth != label and pred == label)
        fn = sum(1 for truth, pred in pairs if truth == label and pred != label)
        support = sum(1 for truth in y_true if truth == label)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        result[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
    return result


def macro_f1(per_class: dict[str, dict[str, float]]) -> float:
    if not per_class:
        return 0.0
    return round(sum(item["f1"] for item in per_class.values()) / len(per_class), 4)


def weighted_f1(per_class: dict[str, dict[str, float]]) -> float:
    total = sum(item["support"] for item in per_class.values())
    if total == 0:
        return 0.0
    return round(sum(item["f1"] * item["support"] for item in per_class.values()) / total, 4)


def balanced_accuracy(y_true: tuple[str, ...], y_pred: tuple[str, ...]) -> float:
    labels = set(y_true)
    if not labels:
        return 0.0
    recalls = []
    for label in labels:
        support = sum(1 for item in y_true if item == label)
        correct = sum(
            1
            for truth, pred in zip(y_true, y_pred, strict=True)
            if truth == label and pred == label
        )
        recalls.append(_safe_div(correct, support))
    return round(sum(recalls) / len(recalls), 4)


def average_precision(y_true: tuple[bool, ...], scores: tuple[float, ...]) -> float | None:
    positives = sum(y_true)
    if positives == 0 or positives == len(y_true):
        return None
    order = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    captured = 0
    area = 0.0
    for rank, index in enumerate(order, start=1):
        if y_true[index]:
            captured += 1
            area += captured / rank
    return round(area / positives, 4)


def roc_auc(y_true: tuple[bool, ...], scores: tuple[float, ...]) -> float | None:
    positives = [scores[i] for i, flag in enumerate(y_true) if flag]
    negatives = [scores[i] for i, flag in enumerate(y_true) if not flag]
    if not positives or not negatives:
        return None
    wins = 0.0
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                wins += 1
            elif pos == neg:
                wins += 0.5
    return round(wins / (len(positives) * len(negatives)), 4)


def summarize_binary(
    y_true: tuple[bool, ...],
    y_pred: tuple[bool, ...],
    scores: tuple[float, ...] | None = None,
) -> dict[str, object]:
    confusion = binary_confusion(y_true, y_pred)
    fnr = _safe_div(confusion.false_negative, confusion.true_positive + confusion.false_negative)
    payload: dict[str, object] = {
        "true_positive": confusion.true_positive,
        "false_positive": confusion.false_positive,
        "true_negative": confusion.true_negative,
        "false_negative": confusion.false_negative,
        "precision": confusion.precision,
        "recall": confusion.recall,
        "f1": confusion.f1,
        "false_positive_rate": confusion.false_positive_rate,
        "false_negative_rate": round(fnr, 4),
        "accuracy": confusion.accuracy,
        "confusion_matrix": confusion.matrix,
        "bootstrap": bootstrap_f1(y_true, y_pred),
        "pr_auc": None,
        "roc_auc": None,
    }
    if scores is not None:
        payload["pr_auc"] = average_precision(y_true, scores)
        payload["roc_auc"] = roc_auc(y_true, scores)
        if payload["roc_auc"] is not None and (math.isnan(payload["roc_auc"])):
            payload["roc_auc"] = None
    return payload


def label_distribution(labels: tuple[str, ...]) -> dict[str, int]:
    return dict(Counter(labels))
