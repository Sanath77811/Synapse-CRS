# Counterfactual reasoning

**Implemented as feature ablation and rule sensitivity**, not causal identification.

`ablate_repeated_network` rebuilds a reconstruction with at most two covering network observations per process identity, then re-runs hybrid assessment. Stored telemetry is not modified.

Do not read the result as “what would have happened on the host.”
