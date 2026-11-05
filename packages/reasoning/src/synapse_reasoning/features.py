"""Versioned feature schema 1.0.0 over reconstructions only."""

from synapse_reasoning import FEATURE_VERSION
from synapse_reasoning.models import FeatureVector, Reconstruction

FEATURE_DEFINITIONS = {
    "process_count": {
        "definition": "Number of reconstructed process identities",
        "type": "float",
        "source": "process lifetimes",
        "window": "full reconstruction",
        "missing": "0",
    },
    "complete_lifecycle_ratio": {
        "definition": "Fraction of identities with both start and exit",
        "type": "float",
        "source": "process lifetimes",
        "window": "full reconstruction",
        "missing": "0",
    },
    "network_count": {
        "definition": "Count of network_connection_observed events",
        "type": "float",
        "source": "observations",
        "window": "full reconstruction",
        "missing": "0",
    },
    "max_network_per_process": {
        "definition": "Maximum covering networks on one pid+start_ticks identity",
        "type": "float",
        "source": "covering lifetimes",
        "window": "full reconstruction",
        "missing": "0",
    },
    "distinct_remote_ports_max": {
        "definition": "Maximum distinct remote_port values on one identity",
        "type": "float",
        "source": "covering network payloads",
        "window": "full reconstruction",
        "missing": "0",
    },
    "event_density": {
        "definition": "Events per second across the reconstruction span",
        "type": "float",
        "source": "observed_at min/max",
        "window": "span of observations",
        "missing": "0",
    },
    "missing_start_count": {
        "definition": "Exits without a matching start",
        "type": "float",
        "source": "process lifetimes",
        "window": "full reconstruction",
        "missing": "0",
    },
    "pid_reuse_finding_count": {
        "definition": "Count of lifecycle_pid_reuse_unresolved findings",
        "type": "float",
        "source": "phase 8 findings",
        "window": "full reconstruction",
        "missing": "0",
    },
    "repeated_network_finding": {
        "definition": "1 if a repeated_network_activity finding exists else 0",
        "type": "float",
        "source": "phase 8 findings",
        "window": "full reconstruction",
        "missing": "0",
    },
    "rapid_burst_finding": {
        "definition": "1 if a rapid_activity_burst finding exists else 0",
        "type": "float",
        "source": "phase 8 findings",
        "window": "full reconstruction",
        "missing": "0",
    },
}


def extract_features(reconstruction: Reconstruction, *, window_seconds: int) -> FeatureVector:
    processes = reconstruction.processes
    observations = reconstruction.observations
    findings = reconstruction.findings
    network = [item for item in observations if item.event_type == "network_connection_observed"]
    ports: dict[str, set[int]] = {}
    for process in processes:
        ports[process.identity_key] = set()
    started = {}
    exited = {}
    from synapse_correlation.identity import covering_identities, index_process_events

    started, exited, _ = index_process_events(observations)
    max_ports = 0.0
    for item in network:
        matches = covering_identities(item, started, exited)
        if len(matches) != 1:
            continue
        key = matches[0].key()
        port = item.payload.get("remote_port")
        if isinstance(port, int):
            ports.setdefault(key, set()).add(port)
    if ports:
        max_ports = float(max(len(value) for value in ports.values()))
    span = 1.0
    if reconstruction.started_at and reconstruction.ended_at:
        span = max((reconstruction.ended_at - reconstruction.started_at).total_seconds(), 1.0)
    values = {
        "process_count": float(len(processes)),
        "complete_lifecycle_ratio": (
            float(sum(1 for item in processes if item.complete) / len(processes))
            if processes
            else 0.0
        ),
        "network_count": float(len(network)),
        "max_network_per_process": float(
            max((len(item.network_event_ids) for item in processes), default=0)
        ),
        "distinct_remote_ports_max": max_ports,
        "event_density": float(len(observations) / span),
        "missing_start_count": float(sum(1 for item in processes if item.started_event_id is None)),
        "pid_reuse_finding_count": float(
            sum(1 for item in findings if item.finding_type == "lifecycle_pid_reuse_unresolved")
        ),
        "repeated_network_finding": float(
            any(item.finding_type == "repeated_network_activity" for item in findings)
        ),
        "rapid_burst_finding": float(
            any(item.finding_type == "rapid_activity_burst" for item in findings)
        ),
    }
    sources = {name: spec["source"] for name, spec in FEATURE_DEFINITIONS.items()}
    return FeatureVector(
        version=FEATURE_VERSION,
        values=values,
        sources=sources,
        window_seconds=window_seconds,
    )


def vector_row(features: FeatureVector) -> list[float]:
    return [features.values[name] for name in FEATURE_DEFINITIONS]
