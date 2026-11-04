# Model evaluation

Dataset: `synthetic_lab_features_v1` (label: synthetic). Train = 30 typical rows. Test = 10 typical + 8 unusual rows constructed by the same generator.

`evaluate_neural_holdout()` reports precision, recall, F1, and false-positive rate on that holdout. These numbers are smoke metrics. They are not enterprise detection rates.

Baselines: Phase 8 rules remain the deterministic finding source. The forest scores feature vectors; it does not replace correlation.

Ablation: counterfactual ablation removes repeated-network volume and re-selects a hypothesis. Phase 10 compares correlation, neural-only, symbolic-only, hybrid, and ablations on constructed reconstructions. No claim that hybrid F1 exceeds Phase 8 on enterprise traffic. Generated numbers: [benchmark-results.md](benchmark-results.md).
