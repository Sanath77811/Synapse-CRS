"""HTTP contracts for hybrid reasoning assessments."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from synapse_contracts.version import CONTRACT_VERSION

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


class ReasoningRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_seconds: Annotated[int, Field(ge=1, le=3600)] = 300
    dataset_label: Literal["synthetic_lab", "live_collector", "unspecified"] = "unspecified"
    proposal_kind: ProposalKind = "recommend_analyst_investigation"
    include_counterfactual: bool = True


class ProposalVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ProposalKind
    authorized: bool = True
    in_scope: bool = True
    human_approved: bool = False


class TimelineItemView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    item_id: str
    timestamp: datetime
    event_id: UUID | None
    event_type: str
    classification: Literal["observed", "correlated", "inferred"]
    supporting_event_ids: list[UUID]
    description: str
    evidence_quality: float
    uncertainty: str


class EvidenceQualityView(BaseModel):
    telemetry_coverage: float
    identity_verification: float
    lifecycle_completeness: float
    correlation_clarity: float
    timestamp_consistency: float
    reconstruction_completeness: float
    notes: list[str]


class HypothesisView(BaseModel):
    hypothesis_id: HypothesisId
    support: float
    status: Literal["selected", "viable", "rejected"]
    rationale: str
    supporting_event_ids: list[UUID]
    contradicting: list[str]
    missing_evidence: list[str]
    rules: list[str]


class NeuralView(BaseModel):
    model_id: str
    model_version: str
    unusualness_score: float
    threshold: float
    unusual: bool
    feature_contributions: list[list[object]]
    limitations: str


class ExplanationView(BaseModel):
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
    event_ids: list[UUID]
    rule_ids: list[str]


class PredictionView(BaseModel):
    prediction_id: UUID
    horizon_seconds: int
    prediction_target: str
    predicted_value: float
    baseline_value: float
    uncertainty: str
    evaluation_status: str
    limitations: str


class CounterfactualView(BaseModel):
    counterfactual_id: UUID
    description: str
    kind: str
    baseline_hypothesis: HypothesisId
    result_hypothesis: HypothesisId
    difference: str
    limitations: str


class VerificationView(BaseModel):
    proposal_id: UUID
    kind: ProposalKind
    policy_version: str
    status: str
    solver_result: str
    constraints: list[str]
    violated: list[str]
    explanation: str
    assumptions: str


class ReconstructionView(BaseModel):
    id: UUID
    target_id: UUID
    dataset_label: str
    started_at: datetime | None
    ended_at: datetime | None
    agent_ids: list[UUID]
    supporting_event_ids: list[UUID]
    missing_evidence: list[str]
    quality: EvidenceQualityView
    timeline: list[TimelineItemView]
    process_count: int
    graph_nodes: int
    graph_edges: int
    created_at: datetime
    contract_version: str = CONTRACT_VERSION


class ReasoningAssessmentView(BaseModel):
    id: UUID
    target_id: UUID
    reconstruction_id: UUID
    created_at: datetime
    engine_version: str
    dataset_label: str
    selected_hypothesis: HypothesisId
    confidence: float
    severity: Literal["info", "low", "medium", "high"]
    uncertainty: str
    quality: EvidenceQualityView
    neural: NeuralView
    hypotheses: list[HypothesisView]
    explanation: ExplanationView
    prediction: PredictionView | None
    counterfactual: CounterfactualView | None
    verification: VerificationView | None
    missing_evidence: list[str]
    limitations: list[str]
    evidence_event_ids: list[UUID]
    contract_version: str = CONTRACT_VERSION


class AssessmentPage(BaseModel):
    items: list[ReasoningAssessmentView]
    limit: int
    offset: int
    total: int
