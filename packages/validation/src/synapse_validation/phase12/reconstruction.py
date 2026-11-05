"""Process-tree reconstruction from source identities. PID is never unique."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from synapse_validation.phase12.records import EndpointRecord


@dataclass(frozen=True)
class ProcessNode:
    identity: str
    sample_id: str
    os_pid: object
    parent_identity: object
    started: object
    ended: object
    source_record_ids: tuple[str, ...]
    complete: bool
    orphan: bool
    identity_provenance: str


@dataclass
class ReconstructionReport:
    process_count: int
    complete_lifecycle_count: int
    orphan_count: int
    pid_reuse_count: int
    missing_parent_count: int
    ordering_violations: int
    unresolved_parent_references: int
    coverage: float
    ambiguity_rate: float
    nodes: tuple[ProcessNode, ...]
    notes: str

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["nodes"] = [asdict(item) for item in self.nodes]
        return payload


def _identity(record: EndpointRecord) -> str | None:
    value = record.source_process_id.value
    if value:
        return str(value)
    return None


def reconstruct(records: tuple[EndpointRecord, ...]) -> ReconstructionReport:
    by_id: dict[str, list[EndpointRecord]] = defaultdict(list)
    for item in records:
        key = _identity(item)
        if key is None:
            continue
        by_id[key].append(item)
    nodes: list[ProcessNode] = []
    identities = set(by_id)
    pid_reuse = 0
    ordering = 0
    unresolved = 0
    by_sample_pid: dict[tuple[str, object], set[str]] = defaultdict(set)
    for identity, group in by_id.items():
        group = sorted(group, key=lambda item: str(item.event_timestamp.value or ""))
        stamps = [str(item.event_timestamp.value or "") for item in group]
        if stamps != sorted(stamps):
            ordering += 1
        first = group[0]
        parent = first.source_parent_process_id.value
        orphan = bool(parent) and str(parent) not in identities
        if orphan:
            unresolved += 1
        ended = any(item.process_end_timestamp.value for item in group)
        if first.os_pid.value is not None:
            by_sample_pid[(first.source_sample_id, first.os_pid.value)].add(identity)
        nodes.append(
            ProcessNode(
                identity=identity,
                sample_id=first.source_sample_id,
                os_pid=first.os_pid.value,
                parent_identity=parent,
                started=first.process_start_timestamp.value or first.event_timestamp.value,
                ended=next(
                    (
                        item.process_end_timestamp.value
                        for item in group
                        if item.process_end_timestamp.value
                    ),
                    None,
                ),
                source_record_ids=tuple(item.source_record_id for item in group),
                complete=bool(
                    (first.process_start_timestamp.value or first.event_timestamp.value) and ended
                ),
                orphan=orphan,
                identity_provenance=first.source_process_id.provenance,
            )
        )
    for keys in by_sample_pid.values():
        if len(keys) > 1:
            pid_reuse += 1
    complete = sum(1 for item in nodes if item.complete)
    orphans = sum(1 for item in nodes if item.orphan)
    coverage = 0.0 if not records else round(len(by_id) / max(len(records), 1), 4)
    ambiguity = 0.0 if not nodes else round(pid_reuse / len(nodes), 4)
    return ReconstructionReport(
        process_count=len(nodes),
        complete_lifecycle_count=complete,
        orphan_count=orphans,
        pid_reuse_count=pid_reuse,
        missing_parent_count=unresolved,
        ordering_violations=ordering,
        unresolved_parent_references=unresolved,
        coverage=coverage,
        ambiguity_rate=ambiguity,
        nodes=tuple(nodes),
        notes=(
            "Structural reconstruction only. Completeness is observed start+term, "
            "not an inferred exit at the observation-window boundary. "
            "No independent process-tree accuracy is claimed without ground-truth edges."
        ),
    )
