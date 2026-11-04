# Phase 13 repository audit

Inspected on branch `cursor/v0.2-telemetry-2464` at commit `3667a72` before Phase 13 edits.

## Reusable components

- Phase 12 `endpoint-evidence-1.0.0` records, JSONL loader, sample-grouped splits.
- Phase 12 structural reconstruction (`pid_hash` identity, PID reuse, orphans).
- Phase 12 explanation citation checks.
- Phase 11 bounded loaders and fail-closed CLI pattern.
- Phase 9/10 metrics (`binary_confusion`) and Isolation Forest usage (no pickle).
- Makefile research-eval targets; generated files under `docs/research/generated/`.

## Missing before this phase

- Bounded acquisition with Content-Length gates.
- Official DMBD label inspection separate from process trees.
- Completeness-aware sample method with abstention.
- Relationship labels (confirmed/probable/unsupported/contradictory).
- Phase 13 runner and `docs/research/phase-13/` outputs.

## Conflicts

- Do not map Windows `pid_hash` onto Linux `(agent_id, boot_id, pid, start_ticks)`.
- Do not reuse Phase 9 hybrid scores on DMBD or flows.
- Do not overwrite `last-run.json`, `phase11-last-run.json`, or `phase12-last-run.json` semantics.

## Security

- External datasets stay out of `telemetry_events`.
- No pickle, no shell, no live mitigation.
- Zip members with `..` or absolute paths are rejected.
- Downloads require HTTPS/HTTP, an allowed suffix, and Content-Length ≤ 8 MiB.

## Research gaps

- DMBD `trees_*.json` shards are ≈1 GB and were not downloaded.
- WinMET and OpTC remain size-blocked.
- No independent process-tree ground truth in this checkout.
