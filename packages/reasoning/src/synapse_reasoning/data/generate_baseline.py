"""Write synthetic Isolation Forest training rows. Lab data only."""

import json
from pathlib import Path

NAMES = [
    "process_count",
    "complete_lifecycle_ratio",
    "network_count",
    "max_network_per_process",
    "distinct_remote_ports_max",
    "event_density",
    "missing_start_count",
    "pid_reuse_finding_count",
    "repeated_network_finding",
    "rapid_burst_finding",
]


def _normal(index: int) -> dict[str, float]:
    return {
        "process_count": 1.0,
        "complete_lifecycle_ratio": 1.0,
        "network_count": float(1 + index % 2),
        "max_network_per_process": float(1 + index % 2),
        "distinct_remote_ports_max": 1.0,
        "event_density": 0.4 + (index % 5) * 0.1,
        "missing_start_count": 0.0,
        "pid_reuse_finding_count": 0.0,
        "repeated_network_finding": 0.0,
        "rapid_burst_finding": 0.0,
    }


def _unusual(index: int) -> dict[str, float]:
    return {
        "process_count": 1.0,
        "complete_lifecycle_ratio": 1.0 if index % 3 else 0.5,
        "network_count": float(6 + index % 4),
        "max_network_per_process": float(6 + index % 4),
        "distinct_remote_ports_max": float(3 + index % 4),
        "event_density": 2.5 + (index % 4) * 0.4,
        "missing_start_count": float(index % 2),
        "pid_reuse_finding_count": float(index % 3 == 0),
        "repeated_network_finding": 1.0,
        "rapid_burst_finding": float(index % 2),
    }


def main() -> None:
    rows = [_normal(index) for index in range(40)]
    rows.extend(_unusual(index) for index in range(8))
    payload = {
        "dataset": "synthetic_lab_features_v1",
        "feature_version": "1.0.0",
        "label": "synthetic",
        "train_count": 30,
        "notes": "Synthetic only. Train=30 typical. Test=10 typical + 8 unusual.",
        "feature_names": NAMES,
        "rows": rows,
    }
    path = Path(__file__).with_name("baseline_features_v1.json")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
