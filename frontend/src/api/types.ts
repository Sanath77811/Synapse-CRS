export type Page<T> = {
  items: T[];
  limit: number;
  offset: number;
  total: number;
};

export type TargetView = {
  id: string;
  name: string;
  owner: string;
  scope: { environment: string; assets: string[]; description: string };
  authorization_status: string;
  authorization_expiry: string;
  allowed_capabilities: string[];
  eligible: boolean;
  eligibility_reasons: string[];
  created_at: string;
  updated_at: string;
};

export type AgentView = {
  id: string;
  target_id: string;
  public_key_hex: string;
  public_key_fingerprint: string;
  key_generation: number;
  status: string;
  enrolled_at: string;
  enrolled_by: string;
  revoked_at: string | null;
  updated_at: string;
};

export type CaseView = {
  id: string;
  target_id: string;
  state: string;
  created_at: string;
  updated_at: string;
  created_by: string;
};

export type TransitionView = {
  id: string;
  case_id: string;
  from_state: string;
  to_state: string;
  actor: string;
  reason: string;
  created_at: string;
  executed: boolean;
};

export type CaseDetail = CaseView & { transitions: TransitionView[] };

export type AuditEventView = {
  id: string;
  sequence: number;
  timestamp: string;
  actor: string;
  event_type: string;
  target_id: string | null;
  case_id: string | null;
  payload: Record<string, unknown>;
  previous_event_hash: string;
  event_hash: string;
};

export type ChainVerificationView = {
  valid: boolean;
  event_count: number;
  head_hash: string | null;
  failure_sequence: number | null;
  failure_reason: string | null;
};

export type RiskFactorView = { code: string; points: number; detail: string };

export type RiskSummaryView = {
  score: number;
  factors: RiskFactorView[];
  finding_count: number;
  formula: string;
};

export type SupportingEventView = {
  event_id: string;
  event_type: string;
  observed_at: string;
  sequence: number;
};

export type FindingView = {
  id: string;
  target_id: string;
  finding_type: string;
  severity: string;
  evidence_strength: string;
  confidence: number;
  epistemic_status: string;
  supporting_event_ids: string[];
  supporting_events: SupportingEventView[];
  explanation: string;
  rules_triggered: string[];
  missing_evidence: string[];
  risk_contribution: number;
  risk_factors: RiskFactorView[];
  agent_id: string;
  boot_id: string;
  window_seconds: number;
  created_at: string;
  updated_at: string;
};

export type CorrelationLinkView = {
  id: string;
  rule_id: string;
  left_event_id: string;
  right_event_id: string;
  agent_id: string;
  boot_id: string;
  process_pid: number | null;
  process_start_ticks: number | null;
  window_seconds: number;
  reason: string;
  left_observed_at: string;
  right_observed_at: string;
  epistemic_status: "correlation";
};

export type TimelineItemView = {
  item_id: string;
  timestamp: string;
  event_id: string | null;
  event_type: string;
  classification: "observed" | "correlated" | "inferred";
  supporting_event_ids: string[];
  description: string;
  evidence_quality: number;
  uncertainty: string;
};

export type EvidenceQualityView = {
  telemetry_coverage: number;
  identity_verification: number;
  lifecycle_completeness: number;
  correlation_clarity: number;
  timestamp_consistency: number;
  reconstruction_completeness: number;
  notes: string[];
};

export type HypothesisView = {
  hypothesis_id: string;
  support: number;
  status: "selected" | "viable" | "rejected";
  rationale: string;
  supporting_event_ids: string[];
  contradicting: string[];
  missing_evidence: string[];
  rules: string[];
};

export type NeuralView = {
  model_id: string;
  model_version: string;
  unusualness_score: number;
  threshold: number;
  unusual: boolean;
  feature_contributions: unknown[][];
  limitations: string;
};

export type ExplanationView = {
  summary: string;
  observed: string;
  correlated: string;
  neural: string;
  symbolic: string;
  hypotheses: string;
  selected: string;
  support: string;
  contradiction: string;
  missing: string;
  uncertainty: string;
  event_ids: string[];
  rule_ids: string[];
};

export type CounterfactualView = {
  counterfactual_id: string;
  description: string;
  kind: string;
  baseline_hypothesis: string;
  result_hypothesis: string;
  difference: string;
  limitations: string;
};

export type VerificationView = {
  proposal_id: string;
  kind: string;
  policy_version: string;
  status: string;
  solver_result: string;
  constraints: string[];
  violated: string[];
  explanation: string;
  assumptions: string;
};

export type ReconstructionView = {
  id: string;
  target_id: string;
  dataset_label: string;
  started_at: string | null;
  ended_at: string | null;
  agent_ids: string[];
  supporting_event_ids: string[];
  missing_evidence: string[];
  quality: EvidenceQualityView;
  timeline: TimelineItemView[];
  process_count: number;
  graph_nodes: number;
  graph_edges: number;
  created_at: string;
};

export type ReasoningAssessmentView = {
  id: string;
  target_id: string;
  reconstruction_id: string;
  created_at: string;
  engine_version: string;
  dataset_label: string;
  selected_hypothesis: string;
  confidence: number;
  severity: string;
  uncertainty: string;
  quality: EvidenceQualityView;
  neural: NeuralView;
  hypotheses: HypothesisView[];
  explanation: ExplanationView;
  prediction: { prediction_id: string; predicted_value: number; baseline_value: number; uncertainty: string; limitations: string } | null;
  counterfactual: CounterfactualView | null;
  verification: VerificationView | null;
  missing_evidence: string[];
  limitations: string[];
  evidence_event_ids: string[];
};

export type HealthView = { status: string; service?: string; version?: string; database?: string };

export type PlatformSnapshot = {
  targets: TargetView[];
  cases: CaseView[];
  agents: AgentView[];
  findings: FindingView[];
  links: CorrelationLinkView[];
  risk: RiskSummaryView | null;
  assessments: ReasoningAssessmentView[];
  timeline: ReconstructionView | null;
  audit: AuditEventView[];
  chain: ChainVerificationView | null;
};
