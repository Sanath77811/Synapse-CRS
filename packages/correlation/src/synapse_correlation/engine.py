"""Run deterministic correlation rules over stored observations."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from synapse_correlation.identity import covering_identities, index_process_events
from synapse_correlation.models import (
    CorrelationLink,
    Finding,
    Observation,
    ProcessIdentity,
    RiskFactor,
    RiskSummary,
)
from synapse_correlation.observations import process_identity_from_payload, timestamp_text
from synapse_correlation.scoring import score_findings, severity_for_score

RULE_LIFECYCLE = "rule.process_lifecycle"
RULE_PROCESS_NETWORK = "rule.process_network"
RULE_REPEATED_NETWORK = "rule.repeated_network"
RULE_MULTI_PORT = "rule.multi_port"
RULE_RAPID = "rule.rapid_window"
RULE_PATTERN = "rule.repeated_pattern"
RULE_EXIT_GAP = "rule.lifecycle_gap"
RULE_PID_REUSE = "rule.pid_reuse"


@dataclass(frozen=True)
class CorrelationConfig:
    window_seconds: int = 300
    repeated_network_threshold: int = 5
    multi_port_threshold: int = 3
    rapid_event_threshold: int = 8
    rapid_window_seconds: int = 2
    repeated_pattern_threshold: int = 3
    max_events: int = 5000


@dataclass(frozen=True)
class CorrelationResult:
    links: tuple[CorrelationLink, ...]
    findings: tuple[Finding, ...]
    risk: RiskSummary
    event_count: int
    window_seconds: int


def correlate(
    observations: tuple[Observation, ...],
    config: CorrelationConfig | None = None,
    *,
    created_at: datetime,
) -> CorrelationResult:
    settings = config or CorrelationConfig()
    ordered = tuple(sorted(observations, key=lambda item: (item.observed_at, item.event_id)))
    if len(ordered) > settings.max_events:
        ordered = ordered[-settings.max_events :]
    started, exited, by_pid = index_process_events(ordered)
    links: list[CorrelationLink] = []
    findings: list[Finding] = []
    links.extend(_lifecycle_links(started, exited, settings))
    findings.extend(_lifecycle_findings(ordered, started, exited, by_pid, settings, created_at))
    network_by_identity, _unbound, ambiguous, net_links = _network_bindings(
        ordered, started, exited, settings
    )
    links.extend(net_links)
    findings.extend(_network_findings(network_by_identity, ambiguous, settings, created_at))
    findings.extend(_rapid_findings(ordered, settings, created_at))
    risk = score_findings(tuple(findings))
    return CorrelationResult(
        links=tuple(links),
        findings=tuple(findings),
        risk=risk,
        event_count=len(ordered),
        window_seconds=settings.window_seconds,
    )


def _lifecycle_links(
    started: dict[ProcessIdentity, Observation],
    exited: dict[ProcessIdentity, Observation],
    settings: CorrelationConfig,
) -> list[CorrelationLink]:
    links: list[CorrelationLink] = []
    for identity, start in started.items():
        exit_event = exited.get(identity)
        if exit_event is None:
            continue
        links.append(
            CorrelationLink(
                rule_id=RULE_LIFECYCLE,
                left_event_id=start.event_id,
                right_event_id=exit_event.event_id,
                target_id=start.target_id,
                agent_id=identity.agent_id,
                boot_id=identity.boot_id,
                process_pid=identity.pid,
                process_start_ticks=identity.start_ticks,
                window_seconds=settings.window_seconds,
                reason=(
                    "process_started and process_exited share agent_id, boot_id, "
                    f"pid={identity.pid}, and start_ticks={identity.start_ticks}"
                ),
                left_observed_at=start.observed_at,
                right_observed_at=exit_event.observed_at,
            )
        )
    return links


def _lifecycle_findings(
    ordered: tuple[Observation, ...],
    started: dict[ProcessIdentity, Observation],
    exited: dict[ProcessIdentity, Observation],
    by_pid: dict[tuple, list[ProcessIdentity]],
    settings: CorrelationConfig,
    created_at: datetime,
) -> list[Finding]:
    findings: list[Finding] = []
    for item in ordered:
        if item.event_type != "process_exited":
            continue
        identity = process_identity_from_payload(item)
        if identity is None:
            continue
        if identity in started:
            continue
        findings.append(
            _finding(
                finding_type="lifecycle_exit_without_start",
                rules=(RULE_EXIT_GAP,),
                events=(item,),
                explanation=(
                    "A process_exited observation has pid and start_ticks that do not "
                    "match any process_started from the same agent_id and boot_id. "
                    "This is missing provenance, not a determination of malice."
                ),
                missing=("process_started for pid+start_ticks",),
                epistemic="inference",
                contribution=15,
                factors=(
                    RiskFactor(
                        code="lifecycle_exit_without_start",
                        points=15,
                        detail=f"pid={identity.pid} start_ticks={identity.start_ticks}",
                    ),
                ),
                strength="medium",
                confidence=0.6,
                identity=identity,
                created_at=created_at,
                window_seconds=settings.window_seconds,
                subject=identity.key(),
            )
        )
    for _pid_key, identities in by_pid.items():
        if len(identities) < 2:
            continue
        ordered_ids = sorted(identities, key=lambda item: started[item].observed_at)
        for previous, current in zip(ordered_ids, ordered_ids[1:], strict=False):
            prev_exit = exited.get(previous)
            current_start = started[current]
            if prev_exit is not None and prev_exit.observed_at <= current_start.observed_at:
                continue
            events = (started[previous], current_start)
            findings.append(
                _finding(
                    finding_type="lifecycle_pid_reuse_unresolved",
                    rules=(RULE_PID_REUSE,),
                    events=events,
                    explanation=(
                        f"Two process_started observations share pid={previous.pid} on the "
                        "same agent_id and boot_id with different start_ticks, and no "
                        "process_exited for the earlier identity precedes the later start. "
                        "PID reuse is expected on Linux; without start_ticks this join "
                        "would be unsafe. This is an identity gap, not proof of compromise."
                    ),
                    missing=("process_exited for the earlier pid+start_ticks",),
                    epistemic="inference",
                    contribution=25,
                    factors=(
                        RiskFactor(
                            code="lifecycle_pid_reuse_unresolved",
                            points=25,
                            detail=(
                                f"pid={previous.pid} ticks={previous.start_ticks} then "
                                f"{current.start_ticks}"
                            ),
                        ),
                    ),
                    strength="high",
                    confidence=0.75,
                    identity=previous,
                    created_at=created_at,
                    window_seconds=settings.window_seconds,
                    subject=f"{previous.key()}|{current.key()}",
                )
            )
    return findings


def _network_bindings(
    ordered: tuple[Observation, ...],
    started: dict[ProcessIdentity, Observation],
    exited: dict[ProcessIdentity, Observation],
    settings: CorrelationConfig,
) -> tuple[
    dict[ProcessIdentity, list[Observation]],
    list[Observation],
    list[Observation],
    list[CorrelationLink],
]:
    by_identity: dict[ProcessIdentity, list[Observation]] = defaultdict(list)
    unbound: list[Observation] = []
    ambiguous: list[Observation] = []
    links: list[CorrelationLink] = []
    for item in ordered:
        if item.event_type != "network_connection_observed":
            continue
        pid = item.payload.get("pid")
        if pid is None:
            unbound.append(item)
            continue
        matches = covering_identities(item, started, exited)
        if len(matches) == 0:
            unbound.append(item)
            continue
        if len(matches) > 1:
            ambiguous.append(item)
            continue
        identity = matches[0]
        by_identity[identity].append(item)
        start = started[identity]
        links.append(
            CorrelationLink(
                rule_id=RULE_PROCESS_NETWORK,
                left_event_id=start.event_id,
                right_event_id=item.event_id,
                target_id=item.target_id,
                agent_id=identity.agent_id,
                boot_id=identity.boot_id,
                process_pid=identity.pid,
                process_start_ticks=identity.start_ticks,
                window_seconds=settings.window_seconds,
                reason=(
                    "network_connection_observed pid matches a process_started with "
                    f"start_ticks={identity.start_ticks} whose lifetime covers "
                    f"{timestamp_text(item.observed_at)}"
                ),
                left_observed_at=start.observed_at,
                right_observed_at=item.observed_at,
            )
        )
    return by_identity, unbound, ambiguous, links


def _network_findings(
    by_identity: dict[ProcessIdentity, list[Observation]],
    ambiguous: list[Observation],
    settings: CorrelationConfig,
    created_at: datetime,
) -> list[Finding]:
    findings: list[Finding] = []
    for identity, rows in by_identity.items():
        if len(rows) >= settings.repeated_network_threshold:
            extra = len(rows) - settings.repeated_network_threshold
            points = min(20, 4 * max(extra, 0) + 4)
            findings.append(
                _finding(
                    finding_type="repeated_network_activity",
                    rules=(RULE_REPEATED_NETWORK, RULE_PROCESS_NETWORK),
                    events=tuple(rows),
                    explanation=(
                        f"{len(rows)} network_connection_observed events correlate to "
                        f"pid={identity.pid} start_ticks={identity.start_ticks} on one "
                        "agent boot. Volume above the lab threshold is a correlation, "
                        "not a verdict that the process is an attack."
                    ),
                    missing=(),
                    epistemic="correlation",
                    contribution=points,
                    factors=(
                        RiskFactor(
                            code="repeated_network_activity",
                            points=points,
                            detail=(
                                f"count={len(rows)} threshold={settings.repeated_network_threshold}"
                            ),
                        ),
                    ),
                    strength=(
                        "high" if len(rows) >= settings.repeated_network_threshold + 3 else "medium"
                    ),
                    confidence=0.8,
                    identity=identity,
                    created_at=created_at,
                    window_seconds=settings.window_seconds,
                    subject=identity.key(),
                )
            )
        ports = {int(row.payload["remote_port"]) for row in rows if "remote_port" in row.payload}
        if len(ports) >= settings.multi_port_threshold:
            extra = len(ports) - settings.multi_port_threshold
            points = min(20, 5 * extra + 5)
            findings.append(
                _finding(
                    finding_type="multi_port_network_activity",
                    rules=(RULE_MULTI_PORT, RULE_PROCESS_NETWORK),
                    events=tuple(rows),
                    explanation=(
                        f"The same process identity observed {len(ports)} distinct remote "
                        "ports. Addresses remain [ip]. Distinct ports are a correlation "
                        "feature for operators, not proof of scanning or compromise."
                    ),
                    missing=(),
                    epistemic="correlation",
                    contribution=points,
                    factors=(
                        RiskFactor(
                            code="multi_port_network_activity",
                            points=points,
                            detail=(
                                f"ports={len(ports)} threshold={settings.multi_port_threshold}"
                            ),
                        ),
                    ),
                    strength="medium",
                    confidence=0.8,
                    identity=identity,
                    created_at=created_at,
                    window_seconds=settings.window_seconds,
                    subject=identity.key(),
                )
            )
        pattern_counts: dict[tuple[object, object], list[Observation]] = defaultdict(list)
        for row in rows:
            key = (row.payload.get("protocol"), row.payload.get("remote_port"))
            pattern_counts[key].append(row)
        for key, group in pattern_counts.items():
            if len(group) < settings.repeated_pattern_threshold:
                continue
            findings.append(
                _finding(
                    finding_type="repeated_observation_pattern",
                    rules=(RULE_PATTERN, RULE_PROCESS_NETWORK),
                    events=tuple(group),
                    explanation=(
                        f"{len(group)} observations repeat protocol={key[0]} "
                        f"remote_port={key[1]} for pid={identity.pid} "
                        f"start_ticks={identity.start_ticks}. This research heuristic "
                        "flags repetition. It is not a compromise determination."
                    ),
                    missing=(),
                    epistemic="correlation",
                    contribution=15,
                    factors=(
                        RiskFactor(
                            code="repeated_observation_pattern",
                            points=15,
                            detail=f"protocol={key[0]} remote_port={key[1]} count={len(group)}",
                        ),
                    ),
                    strength="medium",
                    confidence=0.7,
                    identity=identity,
                    created_at=created_at,
                    window_seconds=settings.window_seconds,
                    subject=f"{identity.key()}|{key[0]}|{key[1]}",
                )
            )
    if ambiguous:
        sample = ambiguous[0]
        findings.append(
            _finding(
                finding_type="lifecycle_pid_reuse_unresolved",
                rules=(RULE_PID_REUSE, RULE_PROCESS_NETWORK),
                events=tuple(ambiguous[:20]),
                explanation=(
                    f"{len(ambiguous)} network observations matched more than one live "
                    "process identity for the same pid. The engine refused to join on "
                    "pid alone."
                ),
                missing=("unique covering start_ticks for the network pid",),
                epistemic="inference",
                contribution=25,
                factors=(
                    RiskFactor(
                        code="lifecycle_pid_reuse_unresolved",
                        points=25,
                        detail=f"ambiguous_network_count={len(ambiguous)}",
                    ),
                ),
                strength="high",
                confidence=0.7,
                identity=ProcessIdentity(
                    agent_id=sample.agent_id,
                    boot_id=sample.boot_id,
                    pid=int(sample.payload.get("pid") or 0),
                    start_ticks=0,
                ),
                created_at=created_at,
                window_seconds=settings.window_seconds,
                subject=f"ambiguous:{sample.agent_id}:{sample.boot_id}:{sample.payload.get('pid')}",
            )
        )
    return findings


def _rapid_findings(
    ordered: tuple[Observation, ...],
    settings: CorrelationConfig,
    created_at: datetime,
) -> list[Finding]:
    findings: list[Finding] = []
    grouped: dict[tuple[UUID, UUID], list[Observation]] = defaultdict(list)
    for item in ordered:
        grouped[(item.agent_id, item.boot_id)].append(item)
    span = timedelta(seconds=settings.rapid_window_seconds)
    for (agent_id, boot_id), rows in grouped.items():
        rows = sorted(rows, key=lambda item: (item.observed_at, item.event_id))
        left = 0
        best: list[Observation] = []
        for right, item in enumerate(rows):
            while rows[left].observed_at + span < item.observed_at:
                left += 1
            window_rows = rows[left : right + 1]
            if len(window_rows) > len(best):
                best = window_rows
        if len(best) < settings.rapid_event_threshold:
            continue
        extra = len(best) - settings.rapid_event_threshold
        points = min(20, 3 * extra + 3)
        sample = best[0]
        findings.append(
            _finding(
                finding_type="rapid_activity_burst",
                rules=(RULE_RAPID,),
                events=tuple(best),
                explanation=(
                    f"{len(best)} observations from one agent_id and boot_id occurred "
                    f"within {settings.rapid_window_seconds} seconds. Burst detection "
                    "is a timing correlation. Short-lived lab processes can look the "
                    "same. It is not labeled as an attack."
                ),
                missing=(),
                epistemic="correlation",
                contribution=points,
                factors=(
                    RiskFactor(
                        code="rapid_activity_burst",
                        points=points,
                        detail=(
                            f"count={len(best)} threshold={settings.rapid_event_threshold} "
                            f"window_s={settings.rapid_window_seconds}"
                        ),
                    ),
                ),
                strength="medium",
                confidence=0.65,
                identity=ProcessIdentity(
                    agent_id=agent_id,
                    boot_id=boot_id,
                    pid=0,
                    start_ticks=0,
                ),
                created_at=created_at,
                window_seconds=settings.rapid_window_seconds,
                subject=f"burst:{agent_id}:{boot_id}:{timestamp_text(best[0].observed_at)}",
                target_id=sample.target_id,
            )
        )
    return findings


def _finding(
    *,
    finding_type: str,
    rules: tuple[str, ...],
    events: tuple[Observation, ...],
    explanation: str,
    missing: tuple[str, ...],
    epistemic: str,
    contribution: int,
    factors: tuple[RiskFactor, ...],
    strength: str,
    confidence: float,
    identity: ProcessIdentity,
    created_at: datetime,
    window_seconds: int,
    subject: str,
    target_id: UUID | None = None,
) -> Finding:
    sample = events[0]
    score = min(100, max(0, contribution))
    return Finding(
        finding_type=finding_type,
        severity=severity_for_score(score),
        evidence_strength=strength,  # type: ignore[arg-type]
        confidence=confidence,
        supporting_event_ids=tuple(item.event_id for item in events),
        explanation=explanation,
        rules_triggered=rules,
        missing_evidence=missing,
        created_at=created_at,
        epistemic_status=epistemic,  # type: ignore[arg-type]
        risk_contribution=score,
        risk_factors=factors,
        target_id=target_id or sample.target_id,
        agent_id=identity.agent_id,
        boot_id=identity.boot_id,
        subject_key=subject,
        window_seconds=window_seconds,
        fingerprint_material={
            "finding_type": finding_type,
            "target_id": str(target_id or sample.target_id),
            "agent_id": str(identity.agent_id),
            "boot_id": str(identity.boot_id),
            "subject": subject,
            "window_seconds": str(window_seconds),
        },
    )
