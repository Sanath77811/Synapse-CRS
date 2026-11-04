# Reproduce research benchmarks

Status: **IMPLEMENTED** for the synthetic harness. CIC-IDS2017: supply your own CSV or skip.

## Command

```bash
make research-eval
```

Equivalent:

```bash
PYTHONPATH=packages/contracts/src:packages/policy/src:packages/audit/src:packages/cases/src:packages/telemetry/src:packages/agent/src:packages/correlation/src:packages/reasoning/src:packages/validation/src:apps/api/src \
  python3 -m synapse_validation
```

Writes:

- `docs/research/generated/last-run.json` (machine-readable)
- `docs/research/benchmark-results.md` (human-readable, generated from that JSON)

Optional CIC-IDS2017 parse (bounded, not enrolled as telemetry):

```bash
export SYNAPSE_CICIDS_CSV=/absolute/path/to/cicids.csv
make research-eval
```

## Configuration recorded in JSON

Experiment ID, dataset name/version/checksum, feature schema, model and rule versions, seed 42, split indices, threshold notes, timestamps, software versions, metrics, limitations.

## What this is not

A rerun of `make research-eval` without CIC files does not produce CIC-IDS2017 detection rates. Synthetic accuracy is not enterprise performance.

Phase 11 is a separate command: [reproduce-phase11.md](reproduce-phase11.md). It does not overwrite Phase 10 JSON.

Phase 12 is a separate command: [reproduce-phase12.md](reproduce-phase12.md). It does not overwrite Phase 10 or Phase 11 JSON.
