"""Versioned sample features. Labels are never features."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from synapse_validation.phase12.reconstruction import ProcessNode
from synapse_validation.phase12.records import EndpointRecord
from synapse_validation.phase13 import FEATURE_SCHEMA

FEATURE_DEFINITIONS: tuple[dict[str, str], ...] = (
    {
        "name": "event_count",
        "derivation": "count of normalized records for the sample",
        "required": "source_sample_id",
        "missing": "0",
    },
    {
        "name": "process_count",
        "derivation": "count of reconstructed process identities",
        "required": "source_process_id",
        "missing": "0",
    },
    {
        "name": "orphan_count",
        "derivation": "parent identity present but not in the sample graph",
        "required": "source_parent_process_id",
        "missing": "0",
    },
    {
        "name": "incomplete_lifecycle_count",
        "derivation": "identities without observed process_term",
        "required": "process_end_timestamp",
        "missing": "0",
    },
    {
        "name": "parent_edge_count",
        "derivation": "nodes whose parent identity is present in the graph",
        "required": "source_parent_process_id",
        "missing": "0",
    },
    {
        "name": "network_ref_count",
        "derivation": "records with observed network_connection_reference",
        "required": "network_connection_reference",
        "missing": "0",
    },
    {
        "name": "completeness_ratio",
        "derivation": "complete identities / process_count",
        "required": "process start and term",
        "missing": "0",
    },
    {
        "name": "pid_reuse_flag",
        "derivation": "1 if two identities share sample and os_pid",
        "required": "os_pid plus stable identity",
        "missing": "0",
    },
)


@dataclass(frozen=True)
class SampleFeatureRow:
    sample_id: str
    values: dict[str, float]
    sources: tuple[str, ...]
    schema: str = FEATURE_SCHEMA


def extract_sample_features(
    records: tuple[EndpointRecord, ...],
    nodes: tuple[ProcessNode, ...],
) -> dict[str, SampleFeatureRow]:
    by_sample: dict[str, list[EndpointRecord]] = defaultdict(list)
    for item in records:
        by_sample[item.source_sample_id].append(item)
    nodes_by: dict[str, list[ProcessNode]] = defaultdict(list)
    for node in nodes:
        nodes_by[node.sample_id].append(node)
    rows: dict[str, SampleFeatureRow] = {}
    for sid, items in by_sample.items():
        group = nodes_by.get(sid, [])
        complete = sum(1 for item in group if item.complete)
        orphans = sum(1 for item in group if item.orphan)
        incomplete = sum(1 for item in group if not item.complete)
        parent_edges = sum(1 for item in group if item.parent_identity and not item.orphan)
        nets = sum(1 for item in items if item.network_connection_reference.value)
        pids: dict[object, set[str]] = defaultdict(set)
        for node in group:
            if node.os_pid is not None:
                pids[node.os_pid].add(node.identity)
        reuse = 1.0 if any(len(ids) > 1 for ids in pids.values()) else 0.0
        process_count = float(len(group))
        values = {
            "event_count": float(len(items)),
            "process_count": process_count,
            "orphan_count": float(orphans),
            "incomplete_lifecycle_count": float(incomplete),
            "parent_edge_count": float(parent_edges),
            "network_ref_count": float(nets),
            "completeness_ratio": 0.0 if not group else complete / process_count,
            "pid_reuse_flag": reuse,
        }
        sources = tuple(item.source_record_id for item in items)
        rows[sid] = SampleFeatureRow(sample_id=sid, values=values, sources=sources)
    return rows
