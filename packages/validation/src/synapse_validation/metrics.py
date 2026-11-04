"""Classification and forecast metrics. No invented probabilities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Confusion:
    labels: tuple[str, ...]
    matrix: tuple[tuple[int, ...], ...]
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    accuracy: float


def _safe_div(num: float, den: float) -> float:
    if den == 0:
        return 0.0
    return num / den


def binary_confusion(y_true: tuple[bool, ...], y_pred: tuple[bool, ...]) -> Confusion:
    if len(y_true) != len(y_pred):
        raise ValueError("label length mismatch")
    tp = fp = tn = fn = 0
    for truth, pred in zip(y_true, y_pred, strict=True):
        if truth and pred:
            tp += 1
        elif not truth and pred:
            fp += 1
        elif not truth and not pred:
            tn += 1
        else:
            fn += 1
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    fpr = _safe_div(fp, fp + tn)
    acc = _safe_div(tp + tn, max(len(y_true), 1))
    return Confusion(
        labels=("negative", "positive"),
        matrix=((tn, fp), (fn, tp)),
        true_positive=tp,
        false_positive=fp,
        true_negative=tn,
        false_negative=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        false_positive_rate=round(fpr, 4),
        accuracy=round(acc, 4),
    )


def multiclass_accuracy(y_true: tuple[str, ...], y_pred: tuple[str, ...]) -> float:
    if not y_true:
        return 0.0
    hits = sum(1 for left, right in zip(y_true, y_pred, strict=True) if left == right)
    return round(hits / len(y_true), 4)


def mae(actual: tuple[float, ...], predicted: tuple[float, ...]) -> float:
    if not actual:
        return 0.0
    total = sum(abs(left - right) for left, right in zip(actual, predicted, strict=True))
    return round(total / len(actual), 4)
