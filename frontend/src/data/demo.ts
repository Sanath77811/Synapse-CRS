import type {
  AgentView,
  AuditEventView,
  CaseDetail,
  ChainVerificationView,
  CorrelationLinkView,
  FindingView,
  ReasoningAssessmentView,
  ReconstructionView,
  RiskSummaryView,
  TargetView,
} from "../api/types";

/** Explicit synthetic lab records. Never presented as enrolled telemetry. */
export const DEMO_BANNER =
  "DEMONSTRATION MODE — synthetic lab records. Not enrolled endpoint telemetry.";

export const DEMO_TARGET_ID = "11111111-1111-4111-8111-111111111111";
export const DEMO_AGENT_ID = "22222222-2222-4222-8222-222222222222";
export const DEMO_CASE_ID = "33333333-3333-4333-8333-333333333333";
export const DEMO_FINDING_ID = "44444444-4444-4444-8444-444444444444";
export const DEMO_ASSESSMENT_ID = "55555555-5555-4555-8555-555555555555";
export const E1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1";
export const E2 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2";
export const E3 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3";

const now = "2026-11-04T14:00:00+00:00";

export const demoTarget: TargetView = {
  id: DEMO_TARGET_ID,
  name: "lab-host-alpha",
  owner: "lab-operator",
  scope: {
    environment: "lab",
    assets: ["lab-host-alpha"],
    description: "Owned laboratory fixture used only for demonstration.",
  },
  authorization_status: "active",
  authorization_expiry: "2027-01-01T00:00:00+00:00",
  allowed_capabilities: ["telemetry.ingest", "reasoning.request", "verification.request"],
  eligible: true,
  eligibility_reasons: [],
  created_at: now,
  updated_at: now,
};

export const demoAgent: AgentView = {
  id: DEMO_AGENT_ID,
  target_id: DEMO_TARGET_ID,
  public_key_hex: "aa".repeat(32),
  public_key_fingerprint: "sha256:demo-fingerprint",
  key_generation: 1,
  status: "active",
  enrolled_at: now,
  enrolled_by: "demo-admin",
  revoked_at: null,
  updated_at: now,
};

export const demoCase: CaseDetail = {
  id: DEMO_CASE_ID,
  target_id: DEMO_TARGET_ID,
  state: "HYPOTHESIS",
  created_at: now,
  updated_at: now,
  created_by: "demo-admin",
  transitions: [
    {
      id: "66666666-6666-4666-8666-666666666661",
      case_id: DEMO_CASE_ID,
      from_state: "AUTHORIZED_TARGET",
      to_state: "OBSERVATION",
      actor: "demo-admin",
      reason: "Begin observation window",
      created_at: now,
      executed: false,
    },
    {
      id: "66666666-6666-4666-8666-666666666662",
      case_id: DEMO_CASE_ID,
      from_state: "OBSERVATION",
      to_state: "EVIDENCE",
      actor: "demo-admin",
      reason: "Evidence package recorded",
      created_at: now,
      executed: false,
    },
    {
      id: "66666666-6666-4666-8666-666666666663",
      case_id: DEMO_CASE_ID,
      from_state: "EVIDENCE",
      to_state: "HYPOTHESIS",
      actor: "demo-admin",
      reason: "Hypothesis stage",
      created_at: now,
      executed: false,
    },
  ],
};

export const demoFinding: FindingView = {
  id: DEMO_FINDING_ID,
  target_id: DEMO_TARGET_ID,
  finding_type: "repeated_network_activity",
  severity: "medium",
  evidence_strength: "medium",
  confidence: 0.62,
  epistemic_status: "correlation",
  supporting_event_ids: [E1, E2, E3],
  supporting_events: [
    { event_id: E1, event_type: "process_started", observed_at: now, sequence: 1 },
    { event_id: E2, event_type: "network_connection_observed", observed_at: now, sequence: 2 },
    { event_id: E3, event_type: "network_connection_observed", observed_at: now, sequence: 3 },
  ],
  explanation:
    "Repeated network observations share process identity (agent, boot, pid, start_ticks). This is a synthetic correlation finding, not malice.",
  rules_triggered: ["process_network_join", "repeated_network_activity"],
  missing_evidence: ["process_exited not observed in window"],
  risk_contribution: 12,
  risk_factors: [{ code: "repeated_network", points: 12, detail: "three observations in window" }],
  agent_id: DEMO_AGENT_ID,
  boot_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  window_seconds: 300,
  created_at: now,
  updated_at: now,
};

export const demoLinks: CorrelationLinkView[] = [
  {
    id: "77777777-7777-4777-8777-777777777771",
    rule_id: "process_network_join",
    left_event_id: E1,
    right_event_id: E2,
    agent_id: DEMO_AGENT_ID,
    boot_id: demoFinding.boot_id,
    process_pid: 4421,
    process_start_ticks: 18022,
    window_seconds: 300,
    reason: "Same process identity on start and connection",
    left_observed_at: now,
    right_observed_at: now,
    epistemic_status: "correlation",
  },
  {
    id: "77777777-7777-4777-8777-777777777772",
    rule_id: "repeated_network_activity",
    left_event_id: E2,
    right_event_id: E3,
    agent_id: DEMO_AGENT_ID,
    boot_id: demoFinding.boot_id,
    process_pid: 4421,
    process_start_ticks: 18022,
    window_seconds: 300,
    reason: "Repeated destination within window",
    left_observed_at: now,
    right_observed_at: now,
    epistemic_status: "correlation",
  },
];

export const demoRisk: RiskSummaryView = {
  score: 12,
  factors: demoFinding.risk_factors,
  finding_count: 1,
  formula: "sum(finding.risk_contribution) clipped to 100 — not a probability",
};

const quality = {
  telemetry_coverage: 0.66,
  identity_verification: 1,
  lifecycle_completeness: 0.5,
  correlation_clarity: 0.8,
  timestamp_consistency: 1,
  reconstruction_completeness: 0.7,
  notes: ["Missing process_exited in the observation window."],
};

export const demoTimeline: ReconstructionView = {
  id: "88888888-8888-4888-8888-888888888888",
  target_id: DEMO_TARGET_ID,
  dataset_label: "synthetic_lab",
  started_at: now,
  ended_at: now,
  agent_ids: [DEMO_AGENT_ID],
  supporting_event_ids: [E1, E2, E3],
  missing_evidence: ["process_exited"],
  quality,
  timeline: [
    {
      item_id: "t1",
      timestamp: now,
      event_id: E1,
      event_type: "process_started",
      classification: "observed",
      supporting_event_ids: [E1],
      description: "Process start observed on lab fixture.",
      evidence_quality: 1,
      uncertainty: "identity verified by enrolled public key in live mode; demo record is unsigned.",
    },
    {
      item_id: "t2",
      timestamp: now,
      event_id: E2,
      event_type: "network_connection_observed",
      classification: "observed",
      supporting_event_ids: [E2],
      description: "Outbound connection observed.",
      evidence_quality: 1,
      uncertainty: "destination is allowlisted lab traffic in this fixture.",
    },
    {
      item_id: "t3",
      timestamp: now,
      event_id: null,
      event_type: "process_network_join",
      classification: "correlated",
      supporting_event_ids: [E1, E2],
      description: "Start and connection share process identity.",
      evidence_quality: 0.9,
      uncertainty: "correlation, not exploitation.",
    },
    {
      item_id: "t4",
      timestamp: now,
      event_id: null,
      event_type: "process_exited",
      classification: "inferred",
      supporting_event_ids: [],
      description: "Exit is not observed; absence is not proof the process still runs.",
      evidence_quality: 0,
      uncertainty: "missing evidence",
    },
  ],
  process_count: 1,
  graph_nodes: 4,
  graph_edges: 3,
  created_at: now,
};

export const demoAssessment: ReasoningAssessmentView = {
  id: DEMO_ASSESSMENT_ID,
  target_id: DEMO_TARGET_ID,
  reconstruction_id: demoTimeline.id,
  created_at: now,
  engine_version: "0.6.0",
  dataset_label: "synthetic_lab",
  selected_hypothesis: "H2_unusual_legitimate",
  confidence: 0.54,
  severity: "low",
  uncertainty: "Scores are not calibrated probabilities. Synthetic lab baseline only.",
  quality,
  neural: {
    model_id: "isolation-forest-synthetic-baseline-v1",
    model_version: "1.0.0",
    unusualness_score: 0.21,
    threshold: 0.4,
    unusual: false,
    feature_contributions: [
      ["repeated_network_volume", 0.18],
      ["process_count", 0.04],
    ],
    limitations: "Fitted on 30 synthetic typical rows. Not CIC-IDS or DMBD.",
  },
  hypotheses: [
    {
      hypothesis_id: "H1_normal",
      support: 0.31,
      status: "viable",
      rationale: "Volume is within some lab traces.",
      supporting_event_ids: [E1],
      contradicting: ["repeated network observations"],
      missing_evidence: [],
      rules: [],
    },
    {
      hypothesis_id: "H2_unusual_legitimate",
      support: 0.54,
      status: "selected",
      rationale: "Repeated connections on a labelled lab fixture.",
      supporting_event_ids: [E1, E2, E3],
      contradicting: [],
      missing_evidence: ["process_exited"],
      rules: ["repeated_network_activity"],
    },
    {
      hypothesis_id: "H3_suspicious_pattern",
      support: 0.12,
      status: "rejected",
      rationale: "No independent malice label. Do not treat as compromise.",
      supporting_event_ids: [],
      contradicting: ["synthetic_lab dataset_label"],
      missing_evidence: ["event-level ground truth"],
      rules: [],
    },
    {
      hypothesis_id: "H4_insufficient_evidence",
      support: 0.28,
      status: "viable",
      rationale: "Lifecycle is incomplete.",
      supporting_event_ids: [],
      contradicting: [],
      missing_evidence: ["process_exited"],
      rules: ["incomplete_lifecycle"],
    },
  ],
  explanation: {
    summary: "Hybrid selected H2 on synthetic lab features. Not a detection of malice.",
    observed: "process_started and two network observations.",
    correlated: "Identity join on agent, boot, pid, start_ticks.",
    neural: "Isolation Forest unusualness below threshold.",
    symbolic: "repeated_network_activity fired; incomplete lifecycle noted.",
    hypotheses: "H2 selected; H3 rejected for lack of malice evidence.",
    selected: "H2_unusual_legitimate",
    support: "Three supporting event ids.",
    contradiction: "H3 conflicts with dataset_label=synthetic_lab.",
    missing: "process_exited",
    uncertainty: "Not a calibrated probability.",
    event_ids: [E1, E2, E3],
    rule_ids: ["repeated_network_activity"],
  },
  prediction: {
    prediction_id: "99999999-9999-4999-8999-999999999999",
    predicted_value: 2,
    baseline_value: 2,
    uncertainty: "Persistence baseline; not a forecast of attacks.",
    limitations: "Event-count prediction did not outperform persistence in Phase 10.",
  },
  counterfactual: {
    counterfactual_id: "aaaaaaa0-aaaa-4aaa-8aaa-aaaaaaaaaaa0",
    description: "Feature ablation: remove repeated_network_volume.",
    kind: "feature_ablation",
    baseline_hypothesis: "H2_unusual_legitimate",
    result_hypothesis: "H1_normal",
    difference: "Selected hypothesis changes when volume is ablated. Not causal inference.",
    limitations: "Ablation is not an intervention on the host.",
  },
  verification: {
    proposal_id: "bbbbbbb0-bbbb-4bbb-8bbb-bbbbbbbbbbb0",
    kind: "recommend_analyst_investigation",
    policy_version: "1.0.0",
    status: "accepted",
    solver_result: "sat",
    constraints: ["executed_is_false", "destructive_is_false", "evidence_present"],
    violated: [],
    explanation: "Recommendation-only proposal satisfies encoded policy. SAT is not real-world safety.",
    assumptions: "No host mitigation is executed.",
  },
  missing_evidence: ["process_exited"],
  limitations: [
    "synthetic_lab dataset",
    "Isolation Forest is not a probability",
    "Z3 SAT is not host safety",
  ],
  evidence_event_ids: [E1, E2, E3],
};

export const demoAudit: AuditEventView[] = [
  {
    id: "ccccccc1-cccc-4ccc-8ccc-ccccccccccc1",
    sequence: 1,
    timestamp: now,
    actor: "demo-admin",
    event_type: "target.created",
    target_id: DEMO_TARGET_ID,
    case_id: null,
    payload: { executed: false },
    previous_event_hash: "0".repeat(64),
    event_hash: "ab".repeat(32),
  },
];

export const demoChain: ChainVerificationView = {
  valid: true,
  event_count: 1,
  head_hash: "ab".repeat(32),
  failure_sequence: null,
  failure_reason: null,
};

export function demoSnapshot() {
  return {
    targets: [demoTarget],
    cases: [demoCase],
    agents: [demoAgent],
    findings: [demoFinding],
    links: demoLinks,
    risk: demoRisk,
    assessments: [demoAssessment],
    timeline: demoTimeline,
    audit: demoAudit,
    chain: demoChain,
  };
}
