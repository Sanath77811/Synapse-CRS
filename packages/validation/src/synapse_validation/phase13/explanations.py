"""Evidence-grounded sample explanations plus stability check."""

from __future__ import annotations

from synapse_validation.phase12.explanations import explain_sample
from synapse_validation.phase12.reconstruction import ProcessNode
from synapse_validation.phase12.records import EndpointRecord
from synapse_validation.phase13.features import SampleFeatureRow
from synapse_validation.phase13.reasoning import predict_row


def evaluate_explanations(
    records: tuple[EndpointRecord, ...],
    nodes: tuple[ProcessNode, ...],
    features: dict[str, SampleFeatureRow],
    thresholds: dict[str, float],
) -> dict[str, object]:
    by_sample: dict[str, list[EndpointRecord]] = {}
    for item in records:
        by_sample.setdefault(item.source_sample_id, []).append(item)
    nodes_by: dict[str, list[ProcessNode]] = {}
    for node in nodes:
        nodes_by.setdefault(node.sample_id, []).append(node)
    known = {item.source_record_id for item in records}
    unsupported = 0
    stable = 0
    compared = 0
    samples = []
    for sid, rows in by_sample.items():
        prediction = predict_row(features[sid], thresholds)
        malicious = prediction["decision"] == "malicious"
        explanation = explain_sample(
            tuple(rows),
            tuple(nodes_by.get(sid, ())),
            predicted_malicious=malicious,
        )
        if any(ref not in known for ref in explanation.source_record_ids):
            unsupported += 1
        unsupported += len(explanation.unsupported_claims)
        samples.append(explanation.as_dict())
        if len(rows) > 1:
            reduced = tuple(rows[:-1])
            again = explain_sample(
                reduced,
                tuple(nodes_by.get(sid, ())),
                predicted_malicious=malicious,
            )
            compared += 1
            if set(again.source_record_ids) <= {item.source_record_id for item in reduced}:
                stable += 1
    empty = explain_sample((), (), predicted_malicious=True)
    return {
        "valid_source_references": unsupported == 0,
        "unsupported_claim_count": unsupported,
        "stability_kept_citations": stable,
        "stability_compared": compared,
        "insufficient_empty_pass": empty.prediction == "insufficient_evidence",
        "sample": samples[:4],
        "notes": (
            "Stability drops the last record of a sample and checks citations remain "
            "inside the remaining set. Not a causal ablation."
        ),
    }
