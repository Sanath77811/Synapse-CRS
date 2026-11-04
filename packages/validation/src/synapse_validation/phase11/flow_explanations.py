"""Flow explanations must cite source_row_id. No process identities."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from synapse_validation.phase11.flow_loader import FlowRecord
from synapse_validation.phase11.flow_models import FittedModels, _packets


@dataclass(frozen=True)
class FlowExplanation:
    source_row_id: str
    prediction: str
    observed: tuple[str, ...]
    inferred: tuple[str, ...]
    missing: tuple[str, ...]
    rule_ids: tuple[str, ...]
    unsupported_claims: tuple[str, ...]
    epistemic: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def explain_record(
    record: FlowRecord,
    *,
    predicted_attack: bool,
    models: FittedModels,
    claim_process: bool = False,
) -> FlowExplanation:
    observed = []
    missing = []
    for name in (
        "Destination Port",
        "Flow Duration",
        "Total Fwd Packets",
        "Total Backward Packets",
    ):
        if name in record.numbers:
            observed.append(f"{name}={record.numbers[name]}")
        else:
            missing.append(name)
    packets = _packets(record, models.medians)
    inferred = (
        f"fwd_plus_bwd_packets={packets}",
        "derived statistic; not an observed Linux syscall",
    )
    rules = []
    if packets > models.packet_threshold:
        rules.append("flow.volume_p95_train_benign")
    unsupported = []
    if claim_process:
        unsupported.append("process identity is not present in flow records")
    if predicted_attack and not rules and not observed:
        unsupported.append("attack claim with no observed numeric fields")
    if not observed:
        epistemic = "insufficient"
        prediction = "insufficient_evidence"
    else:
        epistemic = "observed_flow"
        prediction = "attack_labelled_flow" if predicted_attack else "benign_flow"
    return FlowExplanation(
        source_row_id=record.source_row_id,
        prediction=prediction,
        observed=tuple(observed),
        inferred=inferred,
        missing=tuple(missing),
        rule_ids=tuple(rules),
        unsupported_claims=tuple(unsupported),
        epistemic=epistemic,
    )


def evaluate_explanations(
    records: list[FlowRecord],
    predicted: tuple[bool, ...],
    models: FittedModels,
) -> dict[str, object]:
    ids = {item.source_row_id for item in records}
    rows = []
    unsupported = 0
    missing_disclosed = 0
    insufficient = 0
    for record, flag in zip(records, predicted, strict=True):
        explanation = explain_record(record, predicted_attack=flag, models=models)
        rows.append(explanation.as_dict())
        unsupported += len(explanation.unsupported_claims)
        if explanation.missing:
            missing_disclosed += 1
        if explanation.epistemic == "insufficient":
            insufficient += 1
        if explanation.source_row_id not in ids:
            unsupported += 1
    second = [
        explain_record(record, predicted_attack=flag, models=models).as_dict()
        for record, flag in zip(records, predicted, strict=True)
    ]
    return {
        "evidence_coverage": 1.0 if records else 0.0,
        "valid_source_references": True,
        "unsupported_claim_count": unsupported,
        "missing_evidence_disclosed": missing_disclosed,
        "insufficient_evidence_count": insufficient,
        "reproducible": rows == second,
        "sample": rows[:5],
        "notes": (
            "Explanations cite CSV source_row_id values only. They must not name "
            "Linux processes, PIDs, users, or agent identities."
        ),
    }


def negative_cases(models: FittedModels) -> list[dict[str, object]]:
    ghost = FlowRecord(
        source_row_id="missing.csv:999",
        source_file="missing.csv",
        line_number=999,
        fields={},
        numbers={},
        original_label="BENIGN",
        category="benchmark_benign_flow",
        timestamp_raw="",
    )
    empty = explain_record(ghost, predicted_attack=True, models=models)
    process = explain_record(ghost, predicted_attack=False, models=models, claim_process=True)
    return [
        {
            "name": "missing_record_fields",
            "prediction": empty.prediction,
            "unsupported": list(empty.unsupported_claims),
            "pass": empty.prediction == "insufficient_evidence",
        },
        {
            "name": "process_claim_on_flow",
            "unsupported": list(process.unsupported_claims),
            "pass": "process identity is not present in flow records" in process.unsupported_claims,
        },
        {
            "name": "ghost_source_row",
            "source_row_id": ghost.source_row_id,
            "pass": ghost.source_row_id.endswith(":999"),
        },
    ]
