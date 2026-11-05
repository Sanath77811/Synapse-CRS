"""Chronological event-volume forecast vs persistence and mean baselines."""

from synapse_reasoning.features import extract_features
from synapse_reasoning.prediction import predict_event_volume

from synapse_validation.metrics import mae
from synapse_validation.scenarios import reconstruct_scenario, unusual_volume


def run_prediction_eval() -> dict[str, object]:
    series = (2.0, 2.0, 3.0, 3.0, 8.0, 8.0, 7.0)
    persistence = series[:-1]
    actual = series[1:]
    mean_preds = []
    for index in range(1, len(series)):
        mean_preds.append(sum(series[:index]) / index)
    reconstruction, _ = reconstruct_scenario(unusual_volume(20, 9))
    features = extract_features(reconstruction, window_seconds=300)
    prediction = predict_event_volume(reconstruction, features)
    equal_to_persistence = (
        prediction is not None and prediction.predicted_value == prediction.baseline_value
    )
    return {
        "dataset_class": "synthetic_lab",
        "task": "event_volume_next_window",
        "series": list(series),
        "persistence_mae": mae(actual, persistence),
        "historical_mean_mae": mae(actual, tuple(mean_preds)),
        "model_equals_persistence": equal_to_persistence,
        "measurable_advantage_over_persistence": False,
        "chronological": True,
        "uncertainty": "unquantified; persistence equals the shipped model",
        "notes": (
            "The shipped volume predictor is the persistence baseline. "
            "It provides no measurable advantage over persistence on this series. "
            "Not a labelled attack forecast."
        ),
    }
