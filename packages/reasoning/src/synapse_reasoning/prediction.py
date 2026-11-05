"""Bounded event-volume forecast. Persistence baseline, not attacker intent."""

from uuid import uuid4

from synapse_reasoning import FEATURE_VERSION, MODEL_ID
from synapse_reasoning.models import FeatureVector, Prediction, Reconstruction

HORIZON_SECONDS = 60


def predict_event_volume(
    reconstruction: Reconstruction,
    features: FeatureVector,
) -> Prediction | None:
    if len(reconstruction.observations) < 2 or reconstruction.started_at is None:
        return None
    span = max(
        (reconstruction.ended_at - reconstruction.started_at).total_seconds()
        if reconstruction.ended_at
        else 1.0,
        1.0,
    )
    rate = len(reconstruction.observations) / span
    predicted = rate * HORIZON_SECONDS
    # Persistence baseline: last density equals future density.
    baseline = predicted
    return Prediction(
        prediction_id=uuid4(),
        target_id=reconstruction.target_id,
        model_version=f"{MODEL_ID}:volume-persistence-v1",
        created_at=reconstruction.created_at,
        horizon_seconds=HORIZON_SECONDS,
        prediction_target="expected_event_count_next_window",
        predicted_value=round(predicted, 4),
        baseline_value=round(baseline, 4),
        uncertainty="unquantified on this sample; persistence equals the model",
        evidence_event_ids=reconstruction.supporting_event_ids,
        feature_version=FEATURE_VERSION,
        evaluation_status="experimental_synthetic_only",
        limitations=(
            "Forecasts future observation volume from historical density. "
            "It does not predict attacker intent or compromise. "
            "On this foundation the model is the persistence baseline."
        ),
    )
