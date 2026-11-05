# Phase 10 methodology

Status: **IMPLEMENTED** as a research harness (`packages/validation`). Benchmark execution is **EXPERIMENTAL**. CIC-IDS2017 scoring of Synapse process features is **NOT IMPLEMENTED** because the feature spaces are not comparable.

## Questions

1. Does hybrid neuro-symbolic reasoning provide measurable benefits over standalone machine learning, deterministic correlation, and symbolic reasoning?
2. Evidence traceability, explanation faithfulness, unusual versus malicious distinction, forecast baselines, counterfactual consistency, Z3 policy, and cost.

The harness does not assume hybrid superiority.

## Data classes (kept separate)

| Class | Meaning |
| --- | --- |
| Live signed Linux telemetry | Enrolled agents, Ed25519, `telemetry_events` |
| Synthetic lab telemetry | Constructed reconstructions and `synthetic_lab_features_v1` |
| External labelled benchmarks | Operator-supplied CIC-IDS2017 CSVs, never inserted into the production store |

## Experiments

| ID | Mode | Ground truth |
| --- | --- | --- |
| A | Phase 8 correlation findings | Synthetic scenario class |
| B | Isolation Forest unusual flag | Same classes; neural cannot emit `insufficient` |
| C | Symbolic rules only | Same classes |
| D | Phase 9 hybrid selected hypothesis | Same classes |
| E | Ablations | Neural+symbolic; hybrid without completeness gate |

Unusual volume is **lab network volume**, not malice. Do not read F1 as enterprise detection.

## Splits

Seed 42. Sequential indices are recorded. A–E metrics use the full constructed fixture set because those classifiers are not fitted on the reconstructions. The Isolation Forest remains fitted on the first 30 typical rows of `baseline_features_v1.json` only. Thresholds are not tuned on a final test set of reconstructions.

## Metrics

Classification: TP, FP, TN, FN, precision, recall, F1, FPR, confusion counts, per-class correctness, macro three-class accuracy. PR-AUC and ROC-AUC are omitted on the tiny synthetic holdout (documented, not invented). Anomaly scores are `-decision_function`, not probabilities.

## Re-run

See [guides/reproduce-benchmarks.md](../guides/reproduce-benchmarks.md).
