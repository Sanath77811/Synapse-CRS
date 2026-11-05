# Research benchmark results

Status: **EXPERIMENTAL**. Every number below was generated from
`phase10-research-validation-v1` (`validation_version` 0.7.0).
Synthetic-lab metrics are not enterprise detection performance.

## 1. Executive summary

Hybrid neuro-symbolic reasoning was compared with Phase 8 correlation,
Isolation Forest scoring, and symbolic rules on twelve constructed
synthetic reconstructions (four typical, four unusual-volume, four
identity-gap). CIC-IDS2017 was **not present** in this environment unless
an operator supplied `SYNAPSE_CICIDS_CSV`.

- Correlation 3-class accuracy: **1.0** (synthetic).
- Neural-only 3-class accuracy: **0.3333** (synthetic).
  Neural-only cannot emit the insufficient class.
- Symbolic-only 3-class accuracy: **1.0** (synthetic).
- Hybrid 3-class accuracy: **1.0** (synthetic).
- Persistence advantage: **False**.
- CIC-IDS2017 available: **False**.

## 2. Research objectives

Primary: measure whether hybrid reasoning helps, hurts, or matches
standalone components on documented tasks. Secondary: traceability,
explanation faithfulness, unusual vs malicious distinction, forecast
baselines, counterfactual consistency, Z3 policy, and cost.

## 3. Architecture under evaluation

Engine `0.6.0`.
Feature schema `1.0.0`.
Model `isolation-forest-synthetic-baseline-v1`. Rules `1.0.0`.

## 4. Dataset description

Name `synthetic_labelled_reconstructions_v1` version `0.7.0`.
Size 12 reconstructions.
Labels: `{'typical': 4, 'unusual_volume': 4, 'insufficient': 4}`.
Class: **synthetic_lab**.

## 5. Dataset limitations

- Fixtures are constructed, not captured from production hosts.
- Labels describe lab construction (typical / volume / gap), not attacker intent.
- CIC-IDS2017 is a flow dataset and is not mapped onto process identities.

## 6. Feature compatibility

CIC-IDS adapter available: False.
Compatibility counts: `{'not_available': 7, 'not_comparable': 3}`.
Zero Synapse `synthetic_lab_features_v1` fields are directly compatible with CIC-IDS2017.

## 7. Experimental methodology

Fixed seed 42. Sequential group-or-sequential split recorded; A–E report the
full fixture set because no classifier is fitted on these reconstructions.
Neural thresholds were not tuned on this fixture set.
Split notes: Scenarios are independently constructed fixtures. Sequential split is recorded; reported A–E metrics use the full labelled fixture set because no model is fitted on these reconstructions.

## 8. Baseline results

**A_deterministic_correlation** (synthetic_lab). Task: Phase 8 findings mapped to three classes.

Three-class accuracy=1.0. Unusual-volume precision=1.0 recall=1.0 F1=1.0 FPR=0.0 TP=4 FP=0 TN=8 FN=0. Elapsed=7e-06s.

## 9. Neural-only results

**B_neural_only** (synthetic_lab). Task: Isolation Forest unusual vs not; cannot emit insufficient.

Three-class accuracy=0.3333. Unusual-volume precision=0.0 recall=0.0 F1=0.0 FPR=0.0 TP=0 FP=0 TN=8 FN=4. Elapsed=0.469858s.

Synthetic feature holdout F1=0.0 (precision=0.0, recall=0.0, FPR=0.2). PR-AUC/ROC-AUC: not reported on this tiny holdout.

## 10. Symbolic-only results

**C_symbolic_only** (synthetic_lab). Task: Symbolic rule supports with conservative ties.

Three-class accuracy=1.0. Unusual-volume precision=1.0 recall=1.0 F1=1.0 FPR=0.0 TP=4 FP=0 TN=8 FN=0. Elapsed=0.000398s.

## 11. Hybrid results

**D_hybrid** (synthetic_lab). Task: Phase 9 hybrid selected hypothesis mapped to three classes.

Three-class accuracy=1.0. Unusual-volume precision=1.0 recall=1.0 F1=1.0 FPR=0.0 TP=4 FP=0 TN=8 FN=0. Elapsed=0.413493s.

## 12. Ablation results

**E_neural_plus_symbolic** (synthetic_lab). Task: Neural + symbolic without completeness gate.

Three-class accuracy=1.0. Unusual-volume precision=1.0 recall=1.0 F1=1.0 FPR=0.0 TP=4 FP=0 TN=8 FN=0. Elapsed=0.425857s.

**E_hybrid_without_evidence_quality** (synthetic_lab). Task: Hybrid minus reconstruction-completeness H4 boost.

Three-class accuracy=1.0. Unusual-volume precision=1.0 recall=1.0 F1=1.0 FPR=0.0 TP=4 FP=0 TN=8 FN=0. Elapsed=0.400014s.

## 13. Prediction results

Persistence MAE=1.1667.
Historical-mean MAE=2.3722.
Shipped model equals persistence: True.
Measurable advantage: False.
Measured on synthetic chronological counts. Not a labelled attack forecast.

## 14. Explainability validation

Mean evidence coverage=1.0.
All evidence references valid=True.
All rule IDs traceable=True.
Unsupported claim total=0.

## 15. Counterfactual validation

[
  {
    "name": "remove_influential_network_volume",
    "original_unchanged": true,
    "assumptions_recorded": true,
    "kind": "feature_ablation",
    "baseline_hypothesis": "H3_suspicious_pattern",
    "result_hypothesis": "H1_normal",
    "dependent_outputs_changed": true
  },
  {
    "name": "remove_non_influential_finding",
    "original_unchanged": true,
    "assumptions_recorded": true,
    "kind": "rule_sensitivity",
    "baseline_hypothesis": "H1_normal",
    "result_hypothesis": "H1_normal",
    "dependent_outputs_changed": false
  },
  {
    "name": "repeat_same_scenario",
    "reproducible": true,
    "kind": "feature_ablation",
    "baseline_hypothesis": "H3_suspicious_pattern",
    "result_hypothesis": "H1_normal"
  },
  {
    "name": "invalid_empty_reconstruction",
    "rejected_or_empty": true,
    "notes": "Empty observation sets are not treated as enrolled telemetry."
  }
]

## 16. Formal verification validation

[
  {
    "name": "authorized_proposal",
    "expected_status": "verified_under_model",
    "actual_status": "verified_under_model",
    "expected_solver": "sat",
    "actual_solver": "sat",
    "pass": true,
    "violated": []
  },
  {
    "name": "unauthorized_proposal",
    "expected_status": "rejected_by_policy",
    "actual_status": "rejected_by_policy",
    "expected_solver": "unsat",
    "actual_solver": "unsat",
    "pass": true,
    "violated": [
      "authorized"
    ]
  },
  {
    "name": "out_of_scope_target",
    "expected_status": "rejected_by_policy",
    "actual_status": "rejected_by_policy",
    "expected_solver": "unsat",
    "actual_solver": "unsat",
    "pass": true,
    "violated": [
      "in_scope"
    ]
  },
  {
    "name": "unknown_target_identity",
    "expected_status": "rejected_by_policy",
    "actual_status": "rejected_by_policy",
    "expected_solver": "unsat",
    "actual_solver": "unsat",
    "pass": true,
    "violated": [
      "identity_certain"
    ]
  },
  {
    "name": "missing_evidence",
    "expected_status": "unknown_insufficient_evidence",
    "actual_status": "unknown_insufficient_evidence",
    "expected_solver": "unsat",
    "actual_solver": "unsat",
    "pass": true,
    "violated": [
      "evidence_present"
    ]
  },
  {
    "name": "missing_human_approval",
    "expected_status": "rejected_by_policy",
    "actual_status": "rejected_by_policy",
    "expected_solver": "unsat",
    "actual_solver": "unsat",
    "pass": true,
    "violated": [
      "human_approval_if_impactful"
    ]
  },
  {
    "name": "destructive_action",
    "expected_status": "rejected_by_policy",
    "actual_status": "rejected_by_policy",
    "expected_solver": "unsat",
    "actual_solver": "unsat",
    "pass": true,
    "violated": [
      "destructive_is_false",
      "mitigation_kind_forbidden"
    ]
  },
  {
    "name": "forbidden_mitigation_type",
    "expected_status": "rejected_by_policy",
    "actual_status": "rejected_by_policy",
    "expected_solver": "unsat",
    "actual_solver": "unsat",
    "pass": true,
    "violated": [
      "mitigation_kind_forbidden"
    ]
  },
  {
    "name": "invalid_executed_flag",
    "expected_status": "rejected_by_policy",
    "actual_status": "rejected_by_policy",
    "expected_solver": "unsat",
    "actual_solver": "unsat",
    "pass": true,
    "violated": [
      "executed_is_false"
    ]
  },
  {
    "name": "conflicting_constraints",
    "expected_status": "unknown_insufficient_evidence",
    "actual_status": "unknown_insufficient_evidence",
    "expected_solver": "unsat",
    "actual_solver": "unsat",
    "pass": true,
    "violated": [
      "executed_is_false",
      "destructive_is_false",
      "authorized",
      "in_scope",
      "identity_certain",
      "evidence_present",
      "human_approval_if_impactful",
      "mitigation_kind_forbidden"
    ]
  },
  {
    "name": "solver_timeout",
    "expected_status": "not_verified",
    "actual_status": "not_triggered",
    "expected_solver": "unknown",
    "actual_solver": "timeout_ms=2000",
    "pass": true,
    "violated": [],
    "notes": "TIMEOUT_MS is 2000. This Boolean policy did not time out."
  },
  {
    "name": "unknown_solver_result",
    "expected_status": "not_verified",
    "actual_status": "not_triggered",
    "expected_solver": "unknown",
    "actual_solver": "not_triggered",
    "pass": true,
    "violated": [],
    "notes": "Unknown solver outcomes are coded; they did not occur in this matrix."
  }
]

SAT under the encoded policy is not a proof of real-world safety.
No proposal is executed.

## 17. Performance analysis

{
  "rss_max_kb": 174976,
  "rss_before_kb": 145760,
  "elapsed_seconds": 2.9501
}

Software: {'python': '3.12.3', 'platform': 'Linux-6.12.94+-x86_64-with-glibc2.39', 'sklearn': '1.9.1', 'numpy': '2.5.4'}

## 18. Threats to validity

- Constructed labels can leak the same rules used for detection.
- Twelve scenarios cannot support generalization claims.
- Neural-only three-class accuracy is penalized because it cannot emit `insufficient`.
- CIC-IDS2017, if supplied, remains a different feature space.

## 19. Limitations

- Synthetic reconstructions are not enterprise detection performance.
- CIC-IDS2017 is not bundled and is not comparable to process-level features.
- Hybrid superiority is not assumed.
- SAT under Z3 is not real-world safety.
- Counterfactuals are feature ablation, not causal identification.

## 20. Conclusions

On this synthetic twelve-scenario fixture, hybrid three-class accuracy (1.0) is equal to the best standalone component (1.0). This is not a claim about enterprise detection. Hybrid value on this set is inspected per class in the JSON metrics, especially identity-gap handling versus neural-only.

## 21. Future research

- Operator-supplied CIC-IDS2017 adapter runs (flow-level, labelled as such).
- Larger independently labelled process-level corpora.
- Quantified forecast uncertainty if a non-persistence model is introduced.

