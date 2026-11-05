# Evidence correlation

Phase 8 is a **deterministic evidence correlation foundation**. It reads enrolled, signature-verified telemetry and writes derived links and findings. It does not collect hosts, call a model, or change a system.

Original `telemetry_events` rows are never updated.

## What is correlated

Observations are grouped with **process identity** `(agent_id, boot_id, pid, start_ticks)`. PID alone is never a join key. A network row binds to a process only when exactly one covering lifetime exists for that pid on the same agent boot.

Relationships:

- `process_started` and `process_exited` with the same identity (`rule.process_lifecycle`)
- A process identity and a covering `network_connection_observed` (`rule.process_network`)
- Repeated network rows for one identity (`rule.repeated_network`)
- Distinct remote ports for one identity (`rule.multi_port`)
- Same agent and boot inside a short timing window (`rule.rapid_window`)
- Repeated protocol+remote_port for one identity (`rule.repeated_pattern`)

Configurable `window_seconds` (1–3600, default 300) is stored on each result. Rapid bursts use a separate 2-second window.

## Provenance

Every link stores source event ids, agent id, boot id, timestamps, rule id, window, and a reason string. Findings store supporting event ids, missing evidence, the rules that fired, and an epistemic status:

- **correlation** — a relationship among stored observations
- **inference** — a conclusion from absence or ambiguity (for example an exit with no matching start)

Findings are not observations. The engine does not invent event ids.

## Finding types

These are research heuristics, not proof of compromise:

| Type | Meaning |
|---|---|
| `lifecycle_exit_without_start` | Exit identity has no matching start |
| `lifecycle_pid_reuse_unresolved` | Same pid, different start_ticks, no intervening exit; or ambiguous network join |
| `repeated_network_activity` | Network count at or above 5 for one identity |
| `multi_port_network_activity` | Distinct remote ports at or above 3 |
| `rapid_activity_burst` | At least 8 observations in 2 seconds on one agent boot |
| `repeated_observation_pattern` | Same protocol and remote port at least 3 times |

Severity (`info`/`low`/`medium`/`high`) is derived from the finding’s point contribution. Confidence (`0–1`) and `evidence_strength` measure completeness, not the same axis as severity. Unusual is not labeled malicious.

## Risk score

See the formula in `packages/correlation/src/synapse_correlation/scoring.py`.

`score = min(100, sum of capped groups)`

| Group | Per finding | Group cap |
|---|---|---|
| exit without start | 15 | 30 |
| unresolved pid reuse | 25 | 50 |
| repeated network | 4 at threshold plus 4 per extra, cap 20 | 20 |
| multi-port | 5 at threshold plus 5 per extra, cap 20 | 20 |
| rapid burst | 3 at threshold plus 3 per extra, cap 20 | 20 |
| repeated pattern | 15 | 15 |

A start, one or two connections, and an exit scores **0**. The score is a preliminary attention heuristic.

## Storage

Migration `0005_correlation_findings`:

- `correlation_runs` — each admin run
- `correlation_links` — unique `(target_id, rule_id, left_event_id, right_event_id)`
- `findings` — unique `fingerprint` of type, target, agent, boot, subject, window

Repeated runs update the existing finding row (supporting ids, score, explanation) instead of inserting duplicates. `synapse_app` may SELECT/INSERT runs and links, and SELECT/INSERT/UPDATE findings. DELETE is rejected. Telemetry stays append-only.

Only `identity_status = enrolled` evidence is correlated, at most 5000 newest rows per target.

## HTTP

Writes require admin. Reads accept admin or viewer.

- `POST /api/v1/targets/{target_id}/correlation/runs`
- `GET /api/v1/targets/{target_id}/findings`
- `GET /api/v1/targets/{target_id}/correlations`
- `GET /api/v1/targets/{target_id}/risk`
- `GET /api/v1/findings/{finding_id}`

Responses omit signatures, public keys, and envelope bodies. Supporting events include id, type, timestamp, and sequence.

## Package

`packages/correlation` is pure over `Observation` values. `apps/api` loads envelopes, locks the target, persists derived rows, and appends `correlation.completed` to the audit chain.
