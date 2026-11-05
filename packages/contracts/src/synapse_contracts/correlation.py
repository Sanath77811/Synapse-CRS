"""Read models for correlation runs, links, findings, and risk summaries."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from synapse_contracts.version import CONTRACT_VERSION

FindingType = Literal[
    "lifecycle_exit_without_start",
    "lifecycle_pid_reuse_unresolved",
    "repeated_network_activity",
    "multi_port_network_activity",
    "rapid_activity_burst",
    "repeated_observation_pattern",
]
Severity = Literal["info", "low", "medium", "high"]
EvidenceStrength = Literal["low", "medium", "high"]
EpistemicStatus = Literal["correlation", "inference"]


class CorrelationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_seconds: Annotated[int, Field(ge=1, le=3600)] = 300


class RiskFactorView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str
    points: int
    detail: str


class RiskSummaryView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    score: int
    factors: list[RiskFactorView]
    finding_count: int
    formula: str
    contract_version: str = CONTRACT_VERSION


class CorrelationRunView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    target_id: UUID
    window_seconds: int
    event_count: int
    link_count: int
    finding_count: int
    risk: RiskSummaryView
    created_at: datetime
    actor: str
    contract_version: str = CONTRACT_VERSION


class CorrelationLinkView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    rule_id: str
    left_event_id: UUID
    right_event_id: UUID
    agent_id: UUID
    boot_id: UUID
    process_pid: int | None
    process_start_ticks: int | None
    window_seconds: int
    reason: str
    left_observed_at: datetime
    right_observed_at: datetime
    epistemic_status: Literal["correlation"] = "correlation"


class CorrelationLinkPage(BaseModel):
    items: list[CorrelationLinkView]
    limit: int
    offset: int
    total: int


class SupportingEventView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: UUID
    event_type: str
    observed_at: datetime
    sequence: int


class FindingView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    target_id: UUID
    finding_type: FindingType
    severity: Severity
    evidence_strength: EvidenceStrength
    confidence: float
    epistemic_status: EpistemicStatus
    supporting_event_ids: list[UUID]
    supporting_events: list[SupportingEventView]
    explanation: str
    rules_triggered: list[str]
    missing_evidence: list[str]
    risk_contribution: int
    risk_factors: list[RiskFactorView]
    agent_id: UUID
    boot_id: UUID
    window_seconds: int
    created_at: datetime
    updated_at: datetime
    contract_version: str = CONTRACT_VERSION


class FindingPage(BaseModel):
    items: list[FindingView]
    limit: int
    offset: int
    total: int
