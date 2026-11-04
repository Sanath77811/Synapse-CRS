"""Deterministic correlation rules and transparent scoring."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from synapse_correlation.engine import correlate
from synapse_correlation.identity import covering_identities, index_process_events
from synapse_correlation.models import Observation, ProcessIdentity
from synapse_correlation.scoring import severity_for_score

BASE = datetime(2026, 9, 29, 17, 34, tzinfo=UTC)
TARGET = uuid4()
AGENT = uuid4()
BOOT = uuid4()


def _obs(
    event_type: str,
    sequence: int,
    offset_ms: int,
    **payload: object,
) -> Observation:
    return Observation(
        event_id=uuid4(),
        event_type=event_type,
        target_id=TARGET,
        agent_id=AGENT,
        boot_id=BOOT,
        sequence=sequence,
        observed_at=BASE + timedelta(milliseconds=offset_ms),
        payload=payload,
    )


def _start(sequence: int, offset_ms: int, pid: int, ticks: int) -> Observation:
    return _obs(
        "process_started",
        sequence,
        offset_ms,
        pid=pid,
        ppid=1,
        uid=1000,
        start_ticks=ticks,
        comm="python3",
    )


def _exit(sequence: int, offset_ms: int, pid: int, ticks: int) -> Observation:
    return _obs("process_exited", sequence, offset_ms, pid=pid, start_ticks=ticks)


def _net(sequence: int, offset_ms: int, pid: int | None, port: int) -> Observation:
    return _obs(
        "network_connection_observed",
        sequence,
        offset_ms,
        protocol="tcp",
        local_port=40000,
        remote_port=port,
        remote_address="[ip]",
        uid=1000,
        pid=pid,
    )


def test_normal_lifecycle_has_links_and_zero_risk() -> None:
    start = _start(1, 0, 4242, 100)
    net = _net(2, 200, 4242, 443)
    exited = _exit(3, 400, 4242, 100)
    result = correlate((start, net, exited), created_at=BASE)
    assert result.risk.score == 0
    assert result.findings == ()
    rules = {item.rule_id for item in result.links}
    assert "rule.process_lifecycle" in rules
    assert "rule.process_network" in rules
    lifecycle = next(item for item in result.links if item.rule_id == "rule.process_lifecycle")
    assert lifecycle.process_pid == 4242
    assert lifecycle.process_start_ticks == 100


def test_never_joins_network_on_pid_alone_when_identities_overlap() -> None:
    first = _start(1, 0, 9, 10)
    second = _start(2, 50, 9, 20)
    net = _net(3, 80, 9, 80)
    started, exited, _ = index_process_events((first, second, net))
    matches = covering_identities(net, started, exited)
    assert len(matches) == 2
    result = correlate((first, second, net), created_at=BASE)
    network_links = [item for item in result.links if item.rule_id == "rule.process_network"]
    assert network_links == []
    types = {item.finding_type for item in result.findings}
    assert "lifecycle_pid_reuse_unresolved" in types


def test_exit_without_start_is_inference_not_malice() -> None:
    exited = _exit(1, 0, 50, 9)
    result = correlate((exited,), created_at=BASE)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.finding_type == "lifecycle_exit_without_start"
    assert finding.epistemic_status == "inference"
    assert "malicious" not in finding.explanation.lower()
    assert finding.risk_contribution == 15
    assert result.risk.score == 15
    assert finding.supporting_event_ids == (exited.event_id,)


def test_pid_reuse_after_exit_is_not_inconsistency() -> None:
    first = _start(1, 0, 7, 1)
    exited = _exit(2, 100, 7, 1)
    second = _start(3, 200, 7, 2)
    result = correlate((first, exited, second), created_at=BASE)
    assert all(item.finding_type != "lifecycle_pid_reuse_unresolved" for item in result.findings)
    assert result.risk.score == 0


def test_repeated_and_multi_port_network_are_correlations() -> None:
    start = _start(1, 0, 8, 3)
    nets = [_net(i + 2, 100 * (i + 1), 8, 80 + i) for i in range(6)]
    result = correlate((start, *nets), created_at=BASE)
    types = {item.finding_type for item in result.findings}
    assert "repeated_network_activity" in types
    assert "multi_port_network_activity" in types
    repeated = next(
        item for item in result.findings if item.finding_type == "repeated_network_activity"
    )
    assert repeated.epistemic_status == "correlation"
    assert "not a verdict" in repeated.explanation or "not proof" in repeated.explanation.lower()
    assert repeated.risk_contribution == 8


def test_rapid_burst_uses_time_window() -> None:
    events = [_start(1, 0, 11, 4)]
    events.extend(_net(i + 2, 10 * i, 11, 443) for i in range(8))
    result = correlate(tuple(events), created_at=BASE)
    burst = next(item for item in result.findings if item.finding_type == "rapid_activity_burst")
    assert burst.window_seconds == 2
    assert burst.epistemic_status == "correlation"
    assert burst.risk_contribution >= 3


def test_repeated_pattern_does_not_claim_compromise() -> None:
    start = _start(1, 0, 12, 5)
    nets = [_net(i + 2, 50 * i, 12, 443) for i in range(3)]
    result = correlate((start, *nets), created_at=BASE)
    pattern = next(
        item for item in result.findings if item.finding_type == "repeated_observation_pattern"
    )
    assert "malicious" not in pattern.explanation.lower()
    assert pattern.risk_contribution == 15


def test_severity_bands_are_separate_from_confidence() -> None:
    assert severity_for_score(0) == "info"
    assert severity_for_score(20) == "low"
    assert severity_for_score(40) == "medium"
    assert severity_for_score(70) == "high"
    start = _start(1, 0, 1, 1)
    result = correlate((start,), created_at=BASE)
    assert result.risk.score == 0
    assert all(item.confidence <= 1 for item in result.findings)


def test_process_identity_key_includes_start_ticks() -> None:
    left = ProcessIdentity(agent_id=AGENT, boot_id=BOOT, pid=1, start_ticks=1)
    right = ProcessIdentity(agent_id=AGENT, boot_id=BOOT, pid=1, start_ticks=2)
    assert left.key() != right.key()
    assert UUID(str(AGENT))
