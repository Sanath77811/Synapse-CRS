"""Isolation Forest baseline fitted from versioned synthetic feature rows.

No pickle or joblib dump is used. The forest is fitted in process from
JSON rows plus a fixed seed. Unusualness is -decision_function, a score,
not a calibrated probability. Training data is synthetic lab behaviour.
"""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from sklearn.ensemble import IsolationForest

from synapse_reasoning import FEATURE_VERSION, MODEL_ID
from synapse_reasoning.features import FEATURE_DEFINITIONS, FeatureVector, vector_row
from synapse_reasoning.models import NeuralAssessment

HYPERPARAMS = {
    "n_estimators": 80,
    "max_samples": 30,
    "contamination": 0.1,
    "random_state": 42,
    "n_jobs": 1,
}
DATA_PATH = Path(__file__).resolve().parent / "data" / "baseline_features_v1.json"


def _load_payload() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _load_rows() -> list[list[float]]:
    payload = _load_payload()
    names = list(FEATURE_DEFINITIONS)
    train_count = int(payload.get("train_count", len(payload["rows"])))
    rows = []
    for item in payload["rows"][:train_count]:
        rows.append([float(item[name]) for name in names])
    return rows


def model_version() -> str:
    digest = hashlib.sha256()
    digest.update(DATA_PATH.read_bytes())
    digest.update(json.dumps(HYPERPARAMS, sort_keys=True).encode())
    digest.update(FEATURE_VERSION.encode())
    digest.update(MODEL_ID.encode())
    return f"{MODEL_ID}:{digest.hexdigest()[:16]}"


@lru_cache(maxsize=1)
def _forest() -> tuple[IsolationForest, float]:
    rows = _load_rows()
    forest = IsolationForest(**HYPERPARAMS)
    forest.fit(rows)
    scores = [-float(value) for value in forest.decision_function(rows)]
    scores.sort()
    index = max(0, int(0.90 * (len(scores) - 1)))
    threshold = scores[index]
    return forest, threshold


def score_features(features: FeatureVector) -> NeuralAssessment:
    forest, threshold = _forest()
    row = [vector_row(features)]
    unusualness = -float(forest.decision_function(row)[0])
    contributions: list[tuple[str, float]] = []
    names = list(FEATURE_DEFINITIONS)
    baseline = vector_row(features)
    for index, name in enumerate(names):
        probe = list(baseline)
        probe[index] = 0.0
        probed = -float(forest.decision_function([probe])[0])
        contributions.append((name, round(unusualness - probed, 6)))
    contributions.sort(key=lambda item: abs(item[1]), reverse=True)
    return NeuralAssessment(
        model_id=MODEL_ID,
        model_version=model_version(),
        feature_version=features.version,
        unusualness_score=round(unusualness, 6),
        threshold=round(threshold, 6),
        unusual=unusualness >= threshold,
        feature_contributions=tuple(contributions[:5]),
        limitations=(
            "Isolation Forest fitted on synthetic lab feature rows only. "
            "unusualness_score is -decision_function, not an attack probability."
        ),
    )
