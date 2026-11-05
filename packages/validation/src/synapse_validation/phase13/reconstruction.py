"""Uncertainty-aware reconstruction wrapping Phase 12. No Linux identity invention."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from synapse_validation.phase12.reconstruction import ProcessNode, reconstruct
from synapse_validation.phase12.records import EndpointRecord

Relationship = str  # confirmed | probable | unsupported | none | contradictory


@dataclass(frozen=True)
class AnnotatedNode:
    identity: str
    sample_id: str
    os_pid: object
    parent_identity: object
    children: tuple[str, ...]
    relationship: Relationship
    identity_confidence: str
    complete: bool
    orphan: bool
    source_record_ids: tuple[str, ...]
    contradictions: tuple[str, ...]
    started: object
    ended: object

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _identity_confidence(node: ProcessNode) -> str:
    if node.identity_provenance == "observed":
        return "source_stable"
    if node.identity_provenance == "derived":
        return "derived_fallback"
    return "unresolved"


def annotate(records: tuple[EndpointRecord, ...]) -> dict[str, object]:
    report = reconstruct(records)
    identities = {node.identity for node in report.nodes}
    children: dict[str, list[str]] = defaultdict(list)
    for node in report.nodes:
        parent = str(node.parent_identity) if node.parent_identity else ""
        if parent and parent in identities:
            children[parent].append(node.identity)
    parents_by_id: dict[str, set[object]] = defaultdict(set)
    by_id: dict[str, list[EndpointRecord]] = defaultdict(list)
    for item in records:
        value = item.source_process_id.value
        if value:
            by_id[str(value)].append(item)
            if item.source_parent_process_id.value:
                parents_by_id[str(value)].add(item.source_parent_process_id.value)
    annotated: list[AnnotatedNode] = []
    confirmed = probable = unsupported = contradictory = 0
    for node in report.nodes:
        notes: list[str] = []
        parents = parents_by_id.get(node.identity, set())
        if len(parents) > 1:
            notes.append("conflicting_parent_identifiers")
        if node.started and node.ended and str(node.ended) < str(node.started):
            notes.append("end_before_start")
        parent = node.parent_identity
        if notes:
            relationship: Relationship = "contradictory"
            contradictory += 1
        elif parent and str(parent) in identities:
            derived_parent = any(
                item.source_parent_process_id.provenance == "derived"
                for item in by_id[node.identity]
            )
            if node.identity_provenance == "derived" or derived_parent:
                relationship = "probable"
                probable += 1
            else:
                relationship = "confirmed"
                confirmed += 1
        elif parent:
            relationship = "unsupported"
            unsupported += 1
        else:
            relationship = "none"
        annotated.append(
            AnnotatedNode(
                identity=node.identity,
                sample_id=node.sample_id,
                os_pid=node.os_pid,
                parent_identity=node.parent_identity,
                children=tuple(children.get(node.identity, ())),
                relationship=relationship,
                identity_confidence=_identity_confidence(node),
                complete=node.complete,
                orphan=node.orphan,
                source_record_ids=node.source_record_ids,
                contradictions=tuple(notes),
                started=node.started,
                ended=node.ended,
            )
        )
    return {
        "process_count": report.process_count,
        "complete_lifecycle_count": report.complete_lifecycle_count,
        "orphan_count": report.orphan_count,
        "pid_reuse_count": report.pid_reuse_count,
        "missing_parent_count": report.missing_parent_count,
        "ordering_violations": report.ordering_violations,
        "coverage": report.coverage,
        "ambiguity_rate": report.ambiguity_rate,
        "relationship_counts": {
            "confirmed": confirmed,
            "probable": probable,
            "unsupported": unsupported,
            "contradictory": contradictory,
            "none": max(
                0,
                report.process_count - confirmed - probable - unsupported - contradictory,
            ),
        },
        "notes": (
            report.notes + " Relationship labels are structural, not calibrated probabilities. "
            "Missing termination is not proof the process never exited."
        ),
        "nodes": annotated,
        "base": report,
    }
