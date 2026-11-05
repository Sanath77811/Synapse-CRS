"""In-memory correlation types. These do not mutate stored telemetry."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

EpistemicStatus = Literal["correlation", "inference"]
Severity = Literal["info", "low", "medium", "high"]
EvidenceStrength = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ProcessIdentity:
    agent_id: UUID
    boot_id: UUID
    pid: int
    start_ticks: int

    def key(self) -> str:
        return f"{self.agent_id}:{self.boot_id}:{self.pid}:{self.start_ticks}"


@dataclass(frozen=True)
class Observation:
    event_id: UUID
    event_type: str
    target_id: UUID
    agent_id: UUID
    boot_id: UUID
    sequence: int
    observed_at: datetime
    payload: dict[str, object]


@dataclass(frozen=True)
class CorrelationLink:
    rule_id: str
    left_event_id: UUID
    right_event_id: UUID
    target_id: UUID
    agent_id: UUID
    boot_id: UUID
    process_pid: int | None
    process_start_ticks: int | None
    window_seconds: int
    reason: str
    left_observed_at: datetime
    right_observed_at: datetime


@dataclass(frozen=True)
class RiskFactor:
    code: str
    points: int
    detail: str


@dataclass(frozen=True)
class Finding:
    finding_type: str
    severity: Severity
    evidence_strength: EvidenceStrength
    confidence: float
    supporting_event_ids: tuple[UUID, ...]
    explanation: str
    rules_triggered: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    created_at: datetime
    epistemic_status: EpistemicStatus
    risk_contribution: int
    risk_factors: tuple[RiskFactor, ...]
    target_id: UUID
    agent_id: UUID
    boot_id: UUID
    subject_key: str
    window_seconds: int
    fingerprint_material: dict[str, str]


@dataclass(frozen=True)
class RiskSummary:
    score: int
    factors: tuple[RiskFactor, ...]
    finding_count: int
    formula: str
