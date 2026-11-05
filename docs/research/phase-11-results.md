# Phase 11 research results

Status: **EXPERIMENTAL**. Phase 10 synthetic findings are preserved and are
not reinterpreted here.

## 1. Objectives and research questions

RQ1 flow detection on an independent dataset; RQ2 hybrid benefit given
equivalent inputs; RQ3 traceable explanations; RQ4 robustness; RQ5 what
network flows cannot validate.

## 2. CIC-IDS2017 evaluation status

**cicids2017_evaluated=False**

Blocker: CIC-IDS2017 is not present. Set SYNAPSE_CICIDS_CSV to a local CSV. This command does not download the corpus and does not fall back to fixtures.

No CIC-IDS2017 metrics were produced. Synthetic protocol fixtures
were not substituted for the missing corpus.

## 6. Phase 10 findings (preserved)

```json
{
  "available": true,
  "experiment_id": "phase10-research-validation-v1",
  "dataset": "synthetic_labelled_reconstructions_v1",
  "dataset_class": "synthetic_lab",
  "findings_must_not_be_rewritten": [
    "Correlation, symbolic and hybrid three-class accuracy matched on 12 fixtures.",
    "Hybrid did not outperform simpler approaches on that synthetic set.",
    "Isolation Forest failed unusual-volume reconstructions (F1 0.0).",
    "Prediction equalled persistence.",
    "CIC-IDS2017 was not evaluated in Phase 10."
  ],
  "three_class_accuracy": {
    "A_deterministic_correlation": 1.0,
    "B_neural_only": 0.3333,
    "C_symbolic_only": 1.0,
    "D_hybrid": 1.0,
    "E_neural_plus_symbolic": 1.0,
    "E_hybrid_without_evidence_quality": 1.0
  },
  "neural_holdout_f1": 0.0,
  "prediction_advantage": false,
  "cicids_available_in_phase10": false
}
```

## 7. Capability matrix

[
  {
    "capability": "Flow classification",
    "cicids2017": "Evaluate when files are present",
    "linux_agent_lab": "Not applicable",
    "synthetic_fixtures": "Controlled protocol tests"
  },
  {
    "capability": "Process lifecycle",
    "cicids2017": "Not available",
    "linux_agent_lab": "Evaluate",
    "synthetic_fixtures": "Controlled tests (Phase 10)"
  },
  {
    "capability": "PID reuse",
    "cicids2017": "Not available",
    "linux_agent_lab": "Evaluate",
    "synthetic_fixtures": "Controlled tests (Phase 10)"
  },
  {
    "capability": "Process-network attribution",
    "cicids2017": "Not available",
    "linux_agent_lab": "Evaluate",
    "synthetic_fixtures": "Controlled tests (Phase 10)"
  },
  {
    "capability": "Flow explanation",
    "cicids2017": "Evaluate when files are present",
    "linux_agent_lab": "Only if flow evidence exists",
    "synthetic_fixtures": "Controlled tests"
  },
  {
    "capability": "Endpoint reconstruction",
    "cicids2017": "Not available directly",
    "linux_agent_lab": "Evaluate",
    "synthetic_fixtures": "Controlled tests (Phase 10)"
  },
  {
    "capability": "Agent identity / Ed25519",
    "cicids2017": "Not available",
    "linux_agent_lab": "Evaluate",
    "synthetic_fixtures": "Not a substitute for enrollment"
  },
  {
    "capability": "Phase 9 hybrid on flows",
    "cicids2017": "Not comparable",
    "linux_agent_lab": "Evaluate on reconstructions",
    "synthetic_fixtures": "Phase 10 synthetic reconstructions"
  },
  {
    "capability": "Z3 policy checks",
    "cicids2017": "Not a dataset metric",
    "linux_agent_lab": "Policy tests",
    "synthetic_fixtures": "Policy tests"
  }
]

## 8. Negative findings

- Phase 9 hybrid is not comparable on flow records.
- Phase 10 already showed Isolation Forest failing unusual-volume reconstructions.
- Absence of CIC-IDS2017 is reported as not evaluated, not as a zero score.

## 9. Threats to validity

- Bounded samples are not the full CIC week.
- Rules and forests share the same four numeric fields.
- Temporal splits still share capture artifacts if IPs were used (they are excluded).

## 10. Limitations and future work

- Independent process-level labelled corpora remain the next evidence need.

