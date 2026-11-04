# Reproduce Phase 12

Phase 10: `make research-eval`. Phase 11: `make research-eval-phase11`. Neither is replaced here.

## External DMBD-like JSONL

```bash
export SYNAPSE_DMBD_JSONL=/absolute/path/to/process_rows.jsonl
make research-eval-phase12
```

Exit code **2** if the path is unset. No download, no fixture fallback.

Writes:

- `docs/research/generated/phase12-last-run.json`
- `docs/research/phase-12-results.md`

## Synthetic protocol

```bash
python -m synapse_validation.phase12 --synthetic-protocol tests/fixtures/validation/synthetic_endpoint_protocol.jsonl
```

Label those metrics `synthetic_endpoint_protocol`.
