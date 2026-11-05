"""Rebuild process lifetimes and timelines from enrolled observations.

Inferred timeline items never receive a stored telemetry event_id. PID is
never used without start_ticks.
"""

from uuid import UUID, uuid4

from synapse_correlation.identity import covering_identities, index_process_events
from synapse_correlation.models import CorrelationLink, Finding, Observation
from synapse_correlation.observations import process_identity_from_payload

from synapse_reasoning.models import (
    EvidenceGraph,
    EvidenceQuality,
    GraphEdge,
    GraphNode,
    ProcessLifetime,
    Reconstruction,
    TimelineItem,
)

MAX_GRAPH_NODES = 2000
MAX_GRAPH_EDGES = 5000
MAX_EVENTS = 5000


def reconstruct(
    observations: tuple[Observation, ...],
    findings: tuple[Finding, ...],
    links: tuple[CorrelationLink, ...],
    *,
    created_at,
    dataset_label: str = "unspecified",
) -> Reconstruction:
    ordered = tuple(sorted(observations, key=lambda item: (item.observed_at, item.event_id)))
    truncated = False
    if len(ordered) > MAX_EVENTS:
        ordered = ordered[-MAX_EVENTS:]
        truncated = True
    if not ordered:
        empty_quality = EvidenceQuality(
            telemetry_coverage=0.0,
            identity_verification=0.0,
            lifecycle_completeness=0.0,
            correlation_clarity=1.0,
            timestamp_consistency=1.0,
            reconstruction_completeness=0.0,
            notes=("no enrolled observations",),
        )
        return Reconstruction(
            reconstruction_id=uuid4(),
            target_id=uuid4(),
            started_at=None,
            ended_at=None,
            agent_ids=(),
            timeline=(),
            processes=(),
            findings=findings,
            links=links,
            observations=(),
            supporting_event_ids=(),
            missing_evidence=("enrolled telemetry",),
            alternative_notes=("insufficient evidence",),
            quality=empty_quality,
            graph=EvidenceGraph((), (), False),
            created_at=created_at,
            dataset_label=dataset_label,
        )
    started, exited, by_pid = index_process_events(ordered)
    processes = _lifetimes(ordered, started, exited)
    timeline = _timeline(ordered, findings, processes)
    missing = _missing(processes, findings)
    quality = _quality(ordered, processes, findings, truncated)
    graph = _graph(ordered, processes, findings, links)
    target_id = ordered[0].target_id
    return Reconstruction(
        reconstruction_id=uuid4(),
        target_id=target_id,
        started_at=ordered[0].observed_at,
        ended_at=ordered[-1].observed_at,
        agent_ids=tuple(sorted({item.agent_id for item in ordered})),
        timeline=timeline,
        processes=processes,
        findings=findings,
        links=links,
        observations=ordered,
        supporting_event_ids=tuple(item.event_id for item in ordered),
        missing_evidence=missing,
        alternative_notes=(
            "Alternative explanations are evaluated by the hypothesis engine, "
            "not invented as extra observed events.",
        ),
        quality=quality,
        graph=graph,
        created_at=created_at,
        dataset_label=dataset_label,
    )


def _lifetimes(ordered, started, exited) -> tuple[ProcessLifetime, ...]:
    by_identity: dict = {}
    for identity, start in started.items():
        exit_event = exited.get(identity)
        nets = []
        for item in ordered:
            if item.event_type != "network_connection_observed":
                continue
            matches = covering_identities(item, started, exited)
            if len(matches) == 1 and matches[0] == identity:
                nets.append(item.event_id)
        missing = []
        if exit_event is None:
            missing.append("process_exited")
        by_identity[identity] = ProcessLifetime(
            identity_key=identity.key(),
            agent_id=identity.agent_id,
            boot_id=identity.boot_id,
            pid=identity.pid,
            start_ticks=identity.start_ticks,
            started_event_id=start.event_id,
            exited_event_id=exit_event.event_id if exit_event else None,
            started_at=start.observed_at,
            exited_at=exit_event.observed_at if exit_event else None,
            network_event_ids=tuple(nets),
            complete=exit_event is not None,
            missing=tuple(missing),
        )
    for identity, exit_event in exited.items():
        if identity in by_identity:
            continue
        by_identity[identity] = ProcessLifetime(
            identity_key=identity.key(),
            agent_id=identity.agent_id,
            boot_id=identity.boot_id,
            pid=identity.pid,
            start_ticks=identity.start_ticks,
            started_event_id=None,
            exited_event_id=exit_event.event_id,
            started_at=None,
            exited_at=exit_event.observed_at,
            network_event_ids=(),
            complete=False,
            missing=("process_started",),
        )
    return tuple(sorted(by_identity.values(), key=lambda item: item.identity_key))


def _timeline(ordered, findings, processes) -> tuple[TimelineItem, ...]:
    items: list[TimelineItem] = []
    for obs in ordered:
        identity = process_identity_from_payload(obs)
        items.append(
            TimelineItem(
                item_id=f"obs:{obs.event_id}",
                timestamp=obs.observed_at,
                event_id=obs.event_id,
                event_type=obs.event_type,
                agent_id=obs.agent_id,
                classification="observed",
                supporting_event_ids=(obs.event_id,),
                description=f"Accepted {obs.event_type} sequence={obs.sequence}",
                evidence_quality=1.0,
                uncertainty="",
            )
        )
        if identity is not None:
            del identity
    for finding in findings:
        if not finding.supporting_event_ids:
            continue
        stamp = finding.created_at
        items.append(
            TimelineItem(
                item_id=f"corr:{finding.finding_type}:{finding.subject_key}",
                timestamp=stamp,
                event_id=None,
                event_type=finding.finding_type,
                agent_id=finding.agent_id,
                classification="correlated"
                if finding.epistemic_status == "correlation"
                else "inferred",
                supporting_event_ids=finding.supporting_event_ids,
                description=finding.explanation,
                evidence_quality=finding.confidence,
                uncertainty="Phase 8 finding; not a new observation.",
            )
        )
    for process in processes:
        if process.started_event_id is None and process.exited_event_id is not None:
            items.append(
                TimelineItem(
                    item_id=f"inf:missing-start:{process.identity_key}",
                    timestamp=process.exited_at,
                    event_id=None,
                    event_type="inferred_missing_process_started",
                    agent_id=process.agent_id,
                    classification="inferred",
                    supporting_event_ids=(process.exited_event_id,),
                    description=(
                        "A process_exited identity has no matching process_started. "
                        "This inferred gap is not stored telemetry."
                    ),
                    evidence_quality=0.4,
                    uncertainty="The start may have occurred before the evidence window.",
                )
            )
    items.sort(key=lambda item: (item.timestamp, item.item_id))
    return tuple(items)


def _missing(processes, findings) -> tuple[str, ...]:
    names: list[str] = []
    for process in processes:
        names.extend(process.missing)
    for finding in findings:
        names.extend(finding.missing_evidence)
    return tuple(dict.fromkeys(names))


def _quality(ordered, processes, findings, truncated) -> EvidenceQuality:
    if not processes:
        lifecycle = 0.0
    else:
        lifecycle = sum(1 for item in processes if item.complete) / len(processes)
    ambiguous = sum(1 for item in findings if item.finding_type == "lifecycle_pid_reuse_unresolved")
    clarity = max(0.0, 1.0 - min(1.0, ambiguous / max(len(ordered), 1)))
    stamps = [item.observed_at for item in ordered]
    consistent = 1.0 if stamps == sorted(stamps) else 0.5
    notes = []
    if truncated:
        notes.append("event cap applied")
    coverage = min(1.0, len(ordered) / 3)
    completeness = round((coverage + 1.0 + lifecycle + clarity + consistent) / 5, 4)
    return EvidenceQuality(
        telemetry_coverage=round(coverage, 4),
        identity_verification=1.0,
        lifecycle_completeness=round(lifecycle, 4),
        correlation_clarity=round(clarity, 4),
        timestamp_consistency=consistent,
        reconstruction_completeness=completeness,
        notes=tuple(notes),
    )


def _graph(ordered, processes, findings, links) -> EvidenceGraph:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    def add_node(node_id: str, kind: str, label: str) -> None:
        if node_id not in nodes and len(nodes) < MAX_GRAPH_NODES:
            nodes[node_id] = GraphNode(node_id=node_id, kind=kind, label=label)

    def add_edge(source: str, target: str, relation: str, provenance: str) -> None:
        if len(edges) >= MAX_GRAPH_EDGES:
            return
        if source not in nodes or target not in nodes:
            return
        edges.append(
            GraphEdge(source=source, target=target, relation=relation, provenance=provenance)
        )

    truncated = False
    for obs in ordered:
        add_node(f"event:{obs.event_id}", "event", obs.event_type)
        add_node(f"agent:{obs.agent_id}", "agent", str(obs.agent_id))
        add_edge(
            f"agent:{obs.agent_id}",
            f"event:{obs.event_id}",
            "emitted",
            "observed envelope agent_id",
        )
    for process in processes:
        add_node(f"process:{process.identity_key}", "process", process.identity_key)
        if process.started_event_id:
            add_edge(
                f"event:{process.started_event_id}",
                f"process:{process.identity_key}",
                "starts",
                "pid+start_ticks",
            )
        for event_id in process.network_event_ids:
            add_edge(
                f"event:{event_id}",
                f"process:{process.identity_key}",
                "covers",
                "covering lifetime",
            )
    for finding in findings:
        add_node(
            f"finding:{finding.finding_type}:{finding.subject_key}",
            "finding",
            finding.finding_type,
        )
        for event_id in finding.supporting_event_ids:
            add_edge(
                f"finding:{finding.finding_type}:{finding.subject_key}",
                f"event:{event_id}",
                "supported_by",
                finding.epistemic_status,
            )
    for link in links:
        add_edge(
            f"event:{link.left_event_id}",
            f"event:{link.right_event_id}",
            link.rule_id,
            "phase8_link",
        )
    if len(ordered) >= MAX_EVENTS or len(nodes) >= MAX_GRAPH_NODES:
        truncated = True
    return EvidenceGraph(tuple(nodes.values()), tuple(edges), truncated)


def as_uuid(value: object) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))
