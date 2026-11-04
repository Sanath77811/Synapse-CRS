"""CIC-IDS2017 flow features vs Synapse process-level feature schema 1.0.0."""

from dataclasses import dataclass

Status = str


@dataclass(frozen=True)
class FeatureMap:
    synapse_feature: str
    cicids_fields: tuple[str, ...]
    status: Status
    assumption: str


COMPATIBILITY: tuple[FeatureMap, ...] = (
    FeatureMap(
        "process_count",
        (),
        "not_available",
        "CIC-IDS2017 rows are flows, not process identities.",
    ),
    FeatureMap(
        "complete_lifecycle_ratio",
        (),
        "not_available",
        "No process_started/process_exited in CIC-IDS2017.",
    ),
    FeatureMap(
        "network_count",
        ("Total Fwd Packets", "Total Backward Packets"),
        "not_comparable",
        "Packet counts in one flow are not covering-network counts for a pid+start_ticks lifetime.",
    ),
    FeatureMap(
        "max_network_per_process",
        (),
        "not_available",
        "No process grouping key exists in CIC-IDS2017.",
    ),
    FeatureMap(
        "distinct_remote_ports_max",
        ("Destination Port",),
        "not_comparable",
        "One destination port per flow is not a per-process distinct-port count.",
    ),
    FeatureMap(
        "event_density",
        ("Flow Duration",),
        "not_comparable",
        "Flow duration is not Synapse observation density.",
    ),
    FeatureMap(
        "missing_start_count",
        (),
        "not_available",
        "No process start evidence in CIC-IDS2017.",
    ),
    FeatureMap(
        "pid_reuse_finding_count",
        (),
        "not_available",
        "Phase 8 findings are not CIC-IDS2017 columns.",
    ),
    FeatureMap(
        "repeated_network_finding",
        (),
        "not_available",
        "Phase 8 findings are not CIC-IDS2017 columns.",
    ),
    FeatureMap(
        "rapid_burst_finding",
        (),
        "not_available",
        "Phase 8 findings are not CIC-IDS2017 columns.",
    ),
)


def compatibility_summary() -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in COMPATIBILITY:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts
