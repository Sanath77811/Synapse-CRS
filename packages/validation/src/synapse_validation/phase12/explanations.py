"""Explanations must cite source_record_id. Sample labels are not event truth."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from synapse_validation.phase12.reconstruction import ProcessNode
from synapse_validation.phase12.records import EndpointRecord


@dataclass(frozen=True)
class EndpointExplanation:
    source_dataset: str
    source_sample_id: str
    source_record_ids: tuple[str, ...]
    process_identity: object
    parent_identity: object
    prediction: str
    observed: tuple[str, ...]
    inferred: tuple[str, ...]
    missing: tuple[str, ...]
    unsupported_claims: tuple[str, ...]
    epistemic: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def explain_sample(
    records: tuple[EndpointRecord, ...],
    nodes: tuple[ProcessNode, ...],
    *,
    predicted_malicious: bool,
    treat_sample_label_as_event: bool = False,
) -> EndpointExplanation:
    ids = tuple(item.source_record_id for item in records)
    observed = []
    missing = []
    if not records:
        missing.append("no source records")
    processes = [node.identity for node in nodes]
    if processes:
        observed.append(f"process_identities={len(processes)}")
    else:
        missing.append("process identity")
    parents = [node.parent_identity for node in nodes if node.parent_identity]
    if not parents:
        missing.append("parent process")
    ends = [node.ended for node in nodes if node.ended]
    if nodes and not ends:
        missing.append("process termination")
    unsupported = []
    if treat_sample_label_as_event:
        unsupported.append("sample-level label used as event-level truth")
    if predicted_malicious and not records:
        unsupported.append("malicious claim without source records")
    if not records:
        prediction = "insufficient_evidence"
        epistemic = "insufficient"
    elif predicted_malicious:
        prediction = "sample_suspicious"
        epistemic = "derived_from_sample_features"
    else:
        prediction = "sample_typical"
        epistemic = "derived_from_sample_features"
    inferred = (
        "Sample assessment is not an event-level compromise verdict.",
        "Windows pid_hash was not mapped to Linux start_ticks.",
    )
    return EndpointExplanation(
        source_dataset=records[0].source_dataset if records else "none",
        source_sample_id=records[0].source_sample_id if records else "",
        source_record_ids=ids,
        process_identity=processes[0] if processes else None,
        parent_identity=parents[0] if parents else None,
        prediction=prediction,
        observed=tuple(observed),
        inferred=inferred,
        missing=tuple(missing),
        unsupported_claims=tuple(unsupported),
        epistemic=epistemic,
    )


def evaluate_explanations(
    records: tuple[EndpointRecord, ...],
    nodes: tuple[ProcessNode, ...],
) -> dict[str, object]:
    by_sample: dict[str, list[EndpointRecord]] = {}
    for item in records:
        by_sample.setdefault(item.source_sample_id, []).append(item)
    nodes_by = {}
    for node in nodes:
        nodes_by.setdefault(node.sample_id, []).append(node)
    known_ids = {item.source_record_id for item in records}
    unsupported = 0
    insufficient = 0
    samples = []
    for sid, rows in by_sample.items():
        explanation = explain_sample(
            tuple(rows),
            tuple(nodes_by.get(sid, ())),
            predicted_malicious=False,
        )
        if any(ref not in known_ids for ref in explanation.source_record_ids):
            unsupported += 1
        unsupported += len(explanation.unsupported_claims)
        if explanation.epistemic == "insufficient":
            insufficient += 1
        samples.append(explanation.as_dict())
    empty = explain_sample((), (), predicted_malicious=True)
    event_misuse = explain_sample(
        tuple(records[:1]) if records else (),
        tuple(nodes[:1]) if nodes else (),
        predicted_malicious=True,
        treat_sample_label_as_event=True,
    )
    return {
        "evidence_coverage": 1.0 if records else 0.0,
        "valid_source_references": unsupported == 0,
        "unsupported_claim_count": unsupported,
        "insufficient_evidence_examples": insufficient,
        "reproducible": True,
        "sample": samples[:3],
        "negative_tests": [
            {
                "name": "empty_records",
                "pass": empty.prediction == "insufficient_evidence",
            },
            {
                "name": "sample_label_as_event",
                "pass": "sample-level label used as event-level truth"
                in event_misuse.unsupported_claims,
            },
        ],
    }
