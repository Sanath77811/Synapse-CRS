"""Process identity resolution. PID alone is never a join key."""

from collections import defaultdict

from synapse_correlation.models import Observation, ProcessIdentity
from synapse_correlation.observations import process_identity_from_payload


def index_process_events(
    observations: tuple[Observation, ...],
) -> tuple[
    dict[ProcessIdentity, Observation],
    dict[ProcessIdentity, Observation],
    dict[tuple, list[ProcessIdentity]],
]:
    started: dict[ProcessIdentity, Observation] = {}
    exited: dict[ProcessIdentity, Observation] = {}
    by_pid: dict[tuple, list[ProcessIdentity]] = defaultdict(list)
    for item in observations:
        identity = process_identity_from_payload(item)
        if identity is None:
            continue
        pid_key = (identity.agent_id, identity.boot_id, identity.pid)
        if item.event_type == "process_started":
            started[identity] = item
            if identity not in by_pid[pid_key]:
                by_pid[pid_key].append(identity)
        elif item.event_type == "process_exited":
            exited[identity] = item
    return started, exited, dict(by_pid)


def covering_identities(
    observation: Observation,
    started: dict[ProcessIdentity, Observation],
    exited: dict[ProcessIdentity, Observation],
) -> tuple[ProcessIdentity, ...]:
    """Identities whose lifetime covers a network observation.

    A candidate must share agent_id, boot_id, and pid, and use that
    candidate's start_ticks. PID reuse without an exit yields multiple
    covering identities; the caller must not pick one.
    """
    pid = observation.payload.get("pid")
    if not isinstance(pid, int):
        return ()
    matches: list[ProcessIdentity] = []
    for identity, start in started.items():
        if identity.agent_id != observation.agent_id:
            continue
        if identity.boot_id != observation.boot_id:
            continue
        if identity.pid != pid:
            continue
        if start.observed_at > observation.observed_at:
            continue
        exit_event = exited.get(identity)
        if exit_event is not None and exit_event.observed_at < observation.observed_at:
            continue
        matches.append(identity)
    return tuple(matches)
