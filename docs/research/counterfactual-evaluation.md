# Counterfactual evaluation

Status: **IMPLEMENTED** as **feature ablation** and **rule sensitivity**. Causal identification: **NOT IMPLEMENTED**.

## Distinctions

- Feature ablation: drop or cap inputs, rebuild a derived assessment, compare outputs.
- Sensitivity analysis: omit a finding type while keeping events.
- Causal counterfactuals: would require an intervention model on a host. This repository does not claim that.

## Cases

1. Remove influential repeated-network volume (cap covering nets at two).
2. Remove a non-influential finding type on a typical lifecycle.
3. Repeat the same ablation (reproducibility).
4. Empty observation sets are not enrolled telemetry.

## Invariants

Original reconstruction observations remain unchanged. Baseline hypothesis is recorded. Modified assumptions are stored. Invalid empty inputs are flagged. Identical inputs reproduce the same result hypothesis.
