# Phase 13 reproducibility

## Seeds

Sample splits use the Phase 12 grouped strategy (official split fields when present; otherwise sorted sample ids). Isolation Forest `random_state=42`.

## Bounds

- Max download / JSONL / inspect: 8 MiB
- Max JSONL rows: 5000
- Zip extraction rejects `..` and absolute members

## Outputs

- `docs/research/generated/phase13-last-run.json` (does not replace Phase 10–12 last-run files)
- `docs/research/phase-13/phase-13-results.json`
- `docs/research/phase-13/phase-13-report.md`

## What is not reproducible here

Independent DMBD tree reconstruction, because `trees_*.json` were not acquired.
