# Reasoning demonstration

Synthetic lab envelopes (not `/proc`) are signed, ingested, correlated, then assessed.

```bash
make demo-reasoning
```

The API binds `127.0.0.1:18082`. Stderr `demo_complete` includes `dataset=synthetic_lab`, selected hypothesis, neural unusual flag, reconstruction completeness, counterfactual difference, verification status, and Z3 `unsat` for `execute_host_mitigation`.

Live collector evidence must use a distinct `agent_id` and `dataset_label=live_collector`. Do not mix those event ids with the synthetic stream.
