# Linux telemetry agent

Phase 7 is an observer-only collector. It polls Linux procfs, normalizes observations with the existing Phase 3 allowlist, signs them with a local Ed25519 key, and POSTs to `POST /api/v1/telemetry/ingest`.

It is not a live intrusion-prevention system. It does not execute actions, change processes, or enroll itself.

## Layout

`packages/agent/src/synapse_agent` is the agent package.

| Module | Role |
|---|---|
| `procfs.py` | Process and network table snapshots |
| `collector.py` | Diffs, Phase 3 normalize, Phase 2 sign |
| `keys.py` | Local PKCS#8 key file, mode `0600` |
| `state.py` | Boot id, sequence, bounded pending queue |
| `transport.py` | urllib POST, no redirects |
| `runner.py` | Poll loop, drain, backoff, shutdown |

The agent reuses `normalize_observation` and `sign_event`. It does not duplicate schemas.

## Collection

Basis remains `procfs_poll`.

- **process_started**: a `(pid, start_ticks)` pair present now and absent on the previous poll.
- **process_exited**: a pair that disappeared. This is a later poll absence, not a kernel waitpid result. Exit codes and signals are not collected.
- **network_connection_observed**: new rows in `tcp`, `tcp6`, `udp`, and `udp6` tables. TCP listen rows are omitted. `remote_address` is always `[ip]`.

The first poll is a warm-up snapshot and emits nothing, so a restart does not replay the whole process table.

Polling misses work that starts and ends between scans. Permission errors skip that task. Root is not required. Mapping a network inode to a pid needs readable `/proc/<pid>/fd`; otherwise `pid` is null.

PID reuse is handled by `start_ticks` from `/proc/<pid>/stat`.

## Identity and transport

Administrator enrollment still creates the agent row and registers the public key. The collector never POSTs a public key as proof of enrollment.

Boot identity prefers `/proc/sys/kernel/random/boot_id` when it is a UUID version 4. Sequence numbers are stored in `state.json` before a successful POST so a crash does not reuse `(agent_id, boot_id, sequence)`.

HTTP 201 and 200 remove the queued item. 401, 403, 409, 413, 415, and 422 are permanent for that item (moved to a bounded failed list). Timeouts and 5xx stay in the pending queue with exponential backoff capped at eight seconds and eight attempts.

Untrusted response bodies are parsed only for a short error `code`. Redirects are not followed.

## Local storage

`SYNAPSE_AGENT_HOME` holds:

- `ed25519.pem` — private key, mode `0600`, directory `0700`
- `state.json` — boot id, next sequence, pending and failed items, mode `0600`

Queue size is bounded (`SYNAPSE_AGENT_MAX_PENDING`, `SYNAPSE_AGENT_MAX_STATE_BYTES`). File permission bits are not hardware-backed key protection.

Pending items include the detached signature so a retry can resend the same bytes. They do not include the private key.

## Logging

JSON lines on stderr. Field names that look like secrets are dropped. Signatures, PEM material, and tokens are not logged.

## Security boundaries

- Observer only
- No argv, environment, file contents, or packet bytes
- No self-enrollment
- No administrative routes
- Private key stays on the monitored host
