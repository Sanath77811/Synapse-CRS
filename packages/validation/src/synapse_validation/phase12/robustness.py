"""Synthetic stress tests on endpoint reconstructions."""

from __future__ import annotations

from synapse_validation.phase12.reconstruction import reconstruct
from synapse_validation.phase12.records import EndpointRecord, unavailable


def _replace(record: EndpointRecord, **changes: object) -> EndpointRecord:
    data = record.__dict__.copy()
    data.update(changes)
    return EndpointRecord(**data)


def run_robustness(records: tuple[EndpointRecord, ...]) -> dict[str, object]:
    baseline = reconstruct(records)
    dropped_create = tuple(
        item for item in records if item.event_type not in {"process_create", "process_started"}
    )
    dropped_term = tuple(
        _replace(item, process_end_timestamp=unavailable())
        if item.process_end_timestamp.value
        else item
        for item in records
    )
    reused = list(records)
    if records:
        first = records[0]
        if first.os_pid.value is not None:
            reused.append(
                _replace(
                    first,
                    source_record_id=first.source_record_id + ":reuse",
                    source_process_id=type(first.source_process_id)(
                        value=str(first.source_process_id.value) + ":b",
                        provenance="derived",
                    ),
                    process_start_timestamp=first.process_start_timestamp,
                )
            )
    unordered = tuple(reversed(records))
    missing_parent = tuple(
        _replace(item, source_parent_process_id=unavailable()) for item in records
    )
    unknown_type = records + (
        (
            _replace(
                records[0],
                source_record_id=records[0].source_record_id + ":unk",
                event_type="unknown_event",
            ),
        )
        if records
        else ()
    )
    return {
        "baseline": {
            "process_count": baseline.process_count,
            "orphans": baseline.orphan_count,
            "pid_reuse": baseline.pid_reuse_count,
            "complete": baseline.complete_lifecycle_count,
        },
        "missing_creation_events": reconstruct(dropped_create).as_dict()
        if dropped_create
        else {"notes": "no remaining rows"},
        "missing_termination": {
            "complete": reconstruct(dropped_term).complete_lifecycle_count,
        },
        "pid_reuse_injected": reconstruct(tuple(reused)).pid_reuse_count,
        "reversed_timestamps": reconstruct(unordered).ordering_violations,
        "parents_removed": reconstruct(missing_parent).unresolved_parent_references,
        "unknown_event_types": reconstruct(unknown_type).process_count if unknown_type else 0,
        "perturbations": "synthetic stress tests; not real-world attack evidence",
    }
