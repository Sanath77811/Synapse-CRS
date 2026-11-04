# Reasoning security boundaries

- Admin-only assessment runs and proposal verification; viewers read.
- Enrolled telemetry only.
- No pickle/joblib model files.
- Bounded events (5000), graph size, Z3 timeout 2s, Isolation Forest `n_jobs=1`.
- Findings and assessments may update on fingerprint; telemetry cannot.
- `synapse_app` has no DELETE on reasoning tables.
- Private keys and envelopes are not stored in reasoning tables.
- `INSUFFICIENT_EVIDENCE` / H4, SAT/UNSAT/unknown are first-class outputs.
- No process kill, firewall, shell, or hotpatch from this package.
