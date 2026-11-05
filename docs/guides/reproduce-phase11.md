# Reproduce Phase 11

Phase 10 remains `make research-eval` and writes `docs/research/generated/last-run.json`. Do not treat that file as CIC-IDS2017.

## External CIC-IDS2017

```bash
export SYNAPSE_CICIDS_CSV=/absolute/path/to/file.csv
make research-eval-phase11
```

Exit code **2** if the corpus is missing. The runner does not download data and does not fall back to fixtures.

Writes:

- `docs/research/generated/phase11-last-run.json`
- `docs/research/phase-11-results.md`

## Synthetic protocol (tests / pipeline smoke)

```bash
PYTHONPATH=packages/contracts/src:packages/policy/src:packages/audit/src:packages/cases/src:packages/telemetry/src:packages/agent/src:packages/correlation/src:packages/reasoning/src:packages/validation/src:apps/api/src \
  python3 -m synapse_validation.phase11 --synthetic-protocol tests/fixtures/validation/synthetic_flow_protocol.csv
```

Those metrics must be described as **synthetic_flow_protocol**, not CIC-IDS2017.
