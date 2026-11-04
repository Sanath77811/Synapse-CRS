# Telemetry evidence store

Phase 4 stores **verified** Phase 1 envelopes in PostgreSQL. A row is cryptographic evidence, not an enrollment record.

Three facts stay distinct:

1. The envelope passed Phase 1 validation.
2. Ed25519 verification succeeded for the supplied public key (`signature_verified = true`).
3. Agent identity is **server-derived**. Unknown agents store `identity_status = unverified`. Enrolled, target-authorized agents store `enrolled`. Other identity failures reject the insert. Callers cannot supply this field. See [agent-enrollment.md](agent-enrollment.md).

This module does not collect `/proc`, ingest over HTTP, or write raw observations.

## Table

`telemetry_events` is append-only.

| Column | Role |
|---|---|
| `id` | Internal UUID primary key |
| `event_id` | Envelope event id, unique |
| `target_id`, `agent_id`, `boot_id` | Claimed identifiers from the envelope |
| `event_type`, `sequence`, `observed_at`, `schema_version` | Indexed facts |
| `envelope` | JSONB validated envelope |
| `signature` | Detached standard-base64 Ed25519 signature |
| `public_key_hex` | 32-byte public key as 64 lowercase hex characters |
| `public_key_fingerprint` | `sha256:` plus hex digest of those 32 bytes |
| `signature_verified` | Always true for stored rows |
| `identity_status` | `unverified` or `enrolled`; never caller-supplied |
| `received_at` | Server UTC receipt time |

There is no foreign key to `targets`. A signed event may name a target that is not registered.

Private keys, command lines, raw IP addresses, environment values, and other Phase 3-excluded data are not columns.

## Constraints and indexes

- Unique `event_id`
- Unique `(agent_id, boot_id, sequence)`
- Indexes on `target_id`, `agent_id`, `event_type`, and `(observed_at, event_id)`
- Check constraints on event type, sequence range, schema version, signature shape, key hex, fingerprint, `signature_verified IS TRUE`, and `identity_status IN ('unverified', 'enrolled')`
- Triggers reject `UPDATE`, `DELETE`, and `TRUNCATE`

## Persistence workflow

`persist_verified_event(session, event, signature, public_key)`:

1. Validate the envelope with `TelemetryEnvelope`.
2. Verify with `verify_event` (existing Phase 2 API, including canonicalization).
3. Derive identity from the `agents` table and current target eligibility.
4. Insert in a savepoint.
5. On unique violation, re-read and classify the conflict.

Caller-supplied “already verified” flags and identity labels are ignored. Insert happens only after verification succeeds. Historical rows are never rewritten.

### Duplicate handling

| Case | Result |
|---|---|
| Same `event_id`, canonical envelope, signature, and public key | `status=duplicate`, no second row |
| Same `event_id`, different evidence | `event_id_conflict` |
| Same `(agent_id, boot_id, sequence)`, different `event_id` | `sequence_conflict` |
| Invalid envelope or signature | rejected, no row |

Concurrent exact duplicates: one insert wins; the other hits the unique constraint, re-reads, and returns `duplicate`. Existing rows are never updated.

Sequence uniqueness is per agent and boot. A new `boot_id` may restart sequence at 1. That is not enrollment.

## Retrieval

`get_event_by_id` and `list_events` are read-only. `list_events` orders by `observed_at`, then `event_id`. `limit` is 1–100. Filters are parameterized: target, agent, event type, observation time range. Callers cannot supply SQL.

## Migration and roles

Revision `0003_telemetry_events` follows `0002_enforce_state`. Migrations still run in the one-shot migrate service. The API process still must not receive `MIGRATION_DATABASE_URL`.

`synapse_app` receives `SELECT` and `INSERT` only. It does not receive `UPDATE` or `DELETE`. The migration role remains table owner.

Downgrade drops the triggers, table, and function. It is for laboratory databases, not production history.

## Tests

Integration tests use the existing `synapse_test` database and `synapse_app` role:

```bash
.venv/bin/pytest tests/integration/test_telemetry_store.py
.venv/bin/pytest
```

## Database-backed demonstration

The offline demo does not talk to PostgreSQL. With `DATABASE_URL` for `synapse_app` and migrations applied:

```bash
make demo-persist
```

or

```bash
.venv/bin/python -m synapse_api.telemetry_persist_demo
```

## Limitations

- No HTTP ingestion
- No collector
- Signature verification is not target authorization
- Unknown-agent evidence remains `unverified` by design
- A new boot identity can start a new sequence
- The migration owner can still disable triggers
