# Reproduce Phase 13

Phase 10: `make research-eval`. Phase 11: `make research-eval-phase11`. Phase 12: `make research-eval-phase12`. None of those files are replaced here.

```bash
make research-eval-phase13
```

Exit 2 is expected when process JSONL is absent.

Synthetic protocol:

```bash
PYTHONPATH=packages/contracts/src:packages/policy/src:packages/audit/src:packages/cases/src:packages/telemetry/src:packages/agent/src:packages/correlation/src:packages/reasoning/src:packages/validation/src:apps/api/src \
  python -m synapse_validation.phase13 --synthetic-protocol tests/fixtures/validation/synthetic_endpoint_protocol.jsonl
```

Reports:

- `docs/research/generated/phase13-last-run.json`
- `docs/research/phase-13/phase-13-report.md`
