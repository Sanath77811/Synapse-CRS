"""In-memory reasoning types. Derived only; original telemetry is unchanged."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from synapse_correlation.models import CorrelationLink, Finding, Observation

EpistemicClass = Literal["observed", "correlated", "inferred"]
HypothesisId = Literal[
    "H1_normal",
    "H2_unusual_legitimate",
    "H3_suspicious_pattern",
    "H4_insufficient_evidence",
]
ProposalKind = Literal[
    "request_additional_telemetry",
    "recommend_analyst_investigation",
    "recommend_isolate_lab_target",
    "execute_host_mitigation",
]
VerificationStatus = Literal[
    "verified_under_model",
    "rejected_by_policy",
    "unknown_insufficient_evidence",
    "not_verified",
]
SolverResult = Literal["sat", "unsat", "unknown"]


@dataclass(frozen=True)
class TimelineItem:
    item_id: str
    timestamp: datetime
    event_id: UUID | None
    event_type: str
    agent_id: UUID | None
    classification: EpistemicClass
    supporting_event_ids: tuple[UUID, ...]
    description: str
    evidence_quality: float
    uncertainty: str


@dataclass(frozen=True)
class ProcessLifetime:
    identity_key: str
    agent_id: UUID
    boot_id: UUID
    pid: int
    start_ticks: int
    started_event_id: UUID | None
    exited_event_id: UUID | None
    started_at: datetime | None
    exited_at: datetime | None
    network_event_ids: tuple[UUID, ...]
    complete: bool
    missing: tuple[str, ...]


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    kind: str
    label: str


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    relation: str
    provenance: str


@dataclass(frozen=True)
class EvidenceGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    truncated: bool


@dataclass(frozen=True)
class EvidenceQuality:
    telemetry_coverage: float
    identity_verification: float
    lifecycle_completeness: float
    correlation_clarity: float
    timestamp_consistency: float
    reconstruction_completeness: float
    notes: tuple[str, ...]


@dataclass(frozen=True)
class Reconstruction:
    reconstruction_id: UUID
    target_id: UUID
    started_at: datetime | None
    ended_at: datetime | None
    agent_ids: tuple[UUID, ...]
    timeline: tuple[TimelineItem, ...]
    processes: tuple[ProcessLifetime, ...]
    findings: tuple[Finding, ...]
    links: tuple[CorrelationLink, ...]
    observations: tuple[Observation, ...]
    supporting_event_ids: tuple[UUID, ...]
    missing_evidence: tuple[str, ...]
    alternative_notes: tuple[str, ...]
    quality: EvidenceQuality
    graph: EvidenceGraph
    created_at: datetime
    dataset_label: str


@dataclass(frozen=True)
class FeatureVector:
    version: str
    values: dict[str, float]
    sources: dict[str, str]
    window_seconds: int


@dataclass(frozen=True)
class NeuralAssessment:
    model_id: str
    model_version: str
    feature_version: str
    unusualness_score: float
    threshold: float
    unusual: bool
    feature_contributions: tuple[tuple[str, float], ...]
    limitations: str


@dataclass(frozen=True)
class SymbolicHit:
    rule_id: str
    rule_version: str
    hypothesis: HypothesisId
    support: float
    evidence_event_ids: tuple[UUID, ...]
    missing: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class HypothesisRecord:
    hypothesis_id: HypothesisId
    support: float
    supporting_event_ids: tuple[UUID, ...]
    contradicting: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    rules: tuple[str, ...]
    neural_signal: str
    assumptions: tuple[str, ...]
    rationale: str
    status: Literal["selected", "viable", "rejected"]


@dataclass(frozen=True)
class Explanation:
    summary: str
    observed: str
    correlated: str
    neural: str
    symbolic: str
    hypotheses: str
    selected: str
    support: str
    contradiction: str
    missing: str
    uncertainty: str
    event_ids: tuple[UUID, ...]
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class Prediction:
    prediction_id: UUID
    target_id: UUID
    model_version: str
    created_at: datetime
    horizon_seconds: int
    prediction_target: str
    predicted_value: float
    baseline_value: float
    uncertainty: str
    evidence_event_ids: tuple[UUID, ...]
    feature_version: str
    evaluation_status: str
    limitations: str


@dataclass(frozen=True)
class Counterfactual:
    counterfactual_id: UUID
    baseline_assessment_id: UUID | None
    description: str
    modified_assumptions: tuple[str, ...]
    changed_features: tuple[str, ...]
    unchanged_features: tuple[str, ...]
    baseline_hypothesis: HypothesisId
    result_hypothesis: HypothesisId
    baseline_unusual: bool
    result_unusual: bool
    difference: str
    limitations: str
    kind: Literal["feature_ablation", "rule_sensitivity", "hypothetical_scenario"]


@dataclass(frozen=True)
class DecisionProposal:
    proposal_id: UUID
    kind: ProposalKind
    target_id: UUID
    authorized: bool
    in_scope: bool
    identity_certain: bool
    evidence_present: bool
    human_approved: bool
    destructive: bool
    impactful: bool
    executed: bool
    rationale: str


@dataclass(frozen=True)
class VerificationResult:
    proposal_id: UUID
    policy_version: str
    status: VerificationStatus
    solver_result: SolverResult
    constraints: tuple[str, ...]
    violated: tuple[str, ...]
    missing_preconditions: tuple[str, ...]
    solver: str
    explanation: str
    assumptions: str


@dataclass(frozen=True)
class ReasoningAssessment:
    assessment_id: UUID
    target_id: UUID
    reconstruction_id: UUID
    created_at: datetime
    engine_version: str
    dataset_label: str
    evidence_event_ids: tuple[UUID, ...]
    finding_types: tuple[str, ...]
    quality: EvidenceQuality
    neural: NeuralAssessment
    symbolic_hits: tuple[SymbolicHit, ...]
    hypotheses: tuple[HypothesisRecord, ...]
    selected_hypothesis: HypothesisId
    explanation: Explanation
    prediction: Prediction | None
    counterfactual: Counterfactual | None
    proposal: DecisionProposal | None
    verification: VerificationResult | None
    confidence: float
    severity: Literal["info", "low", "medium", "high"]
    uncertainty: str
    missing_evidence: tuple[str, ...]
    limitations: tuple[str, ...]
    fingerprint: str
    features: FeatureVector = field(repr=False)
