"""Synthetic labelled reconstructions. Not live Linux telemetry."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from synapse_correlation.engine import correlate
from synapse_correlation.models import Observation
from synapse_reasoning.reconstruction import reconstruct

BASE = datetime(2026, 9, 29, 17, 34, tzinfo=UTC)
TARGET = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
AGENT = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
BOOT = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _obs(event_type: str, sequence: int, seconds: int, **payload: object) -> Observation:
    return Observation(
        event_id=uuid4(),
        event_type=event_type,
        target_id=TARGET,
        agent_id=AGENT,
        boot_id=BOOT,
        sequence=sequence,
        observed_at=BASE + timedelta(seconds=seconds),
        payload=payload,
    )


def typical(pid: int, start_ticks: int) -> tuple[Observation, ...]:
    return (
        _obs(
            "process_started",
            1,
            0,
            pid=pid,
            ppid=1,
            uid=1000,
            start_ticks=start_ticks,
            comm="python3",
        ),
        _obs(
            "network_connection_observed",
            2,
            1,
            protocol="tcp",
            local_port=40000,
            remote_port=443,
            remote_address="[ip]",
            uid=1000,
            pid=pid,
        ),
        _obs("process_exited", 3, 2, pid=pid, start_ticks=start_ticks),
    )


def unusual_volume(pid: int, start_ticks: int) -> tuple[Observation, ...]:
    start = _obs(
        "process_started",
        1,
        0,
        pid=pid,
        ppid=1,
        uid=1000,
        start_ticks=start_ticks,
        comm="python3",
    )
    nets = [
        _obs(
            "network_connection_observed",
            index + 2,
            index + 1,
            protocol="tcp",
            local_port=41000 + index,
            remote_port=80 + index,
            remote_address="[ip]",
            uid=1000,
            pid=pid,
        )
        for index in range(6)
    ]
    return (start, *nets)


def identity_gap(pid: int, start_ticks: int) -> tuple[Observation, ...]:
    return (_obs("process_exited", 1, 0, pid=pid, start_ticks=start_ticks),)


def contradictory(pid: int, start_ticks: int) -> tuple[Observation, ...]:
    """Complete lifecycle plus high network volume (findings vs complete start/exit)."""
    return unusual_volume(pid, start_ticks) + (
        _obs("process_exited", 8, 8, pid=pid, start_ticks=start_ticks),
    )


def labelled_scenarios() -> tuple[dict[str, object], ...]:
    rows = []
    for index in range(4):
        rows.append(
            {
                "scenario_id": f"typical-{index}",
                "truth": "typical",
                "observations": typical(10 + index, 1 + index),
                "dataset_class": "synthetic_lab",
            }
        )
        rows.append(
            {
                "scenario_id": f"volume-{index}",
                "truth": "unusual_volume",
                "observations": unusual_volume(20 + index, 9 + index),
                "dataset_class": "synthetic_lab",
            }
        )
        rows.append(
            {
                "scenario_id": f"gap-{index}",
                "truth": "insufficient",
                "observations": identity_gap(50 + index, 3 + index),
                "dataset_class": "synthetic_lab",
            }
        )
    return tuple(rows)


def reconstruct_scenario(observations: tuple[Observation, ...]):
    correlated = correlate(observations, created_at=BASE)
    reconstruction = reconstruct(
        observations,
        correlated.findings,
        correlated.links,
        created_at=BASE,
        dataset_label="synthetic_lab",
    )
    return reconstruction, correlated
