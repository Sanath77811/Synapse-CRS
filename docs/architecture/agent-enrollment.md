# Agent enrollment and identity

Phase 5 binds an agent identifier to one Ed25519 public key and one authorized target. It reuses the v0.1 target registry, eligibility rules, administrator role, audit chain, and database-role split.

A valid telemetry signature still means only that the caller possessed the private key matching the supplied public key. It does not enroll an agent and does not authorize a target.

## Agent identity model

Table `agents` stores the current registration. Private keys are never a column, never accepted on the API, and never written to audit payloads.

| Column | Role |
|---|---|
| `id` | Agent UUID, unique |
| `target_id` | Foreign key to `targets.id`; immutable after insert |
| `public_key_hex` | Canonical 32-byte Ed25519 public key as 64 lowercase hex characters; unique |
| `public_key_fingerprint` | Server-computed `sha256:` digest of those 32 bytes |
| `key_generation` | Starts at 1; increments on administrator rotation |
| `status` | `active` or `revoked` |
| `enrolled_at`, `enrolled_by` | Immutable enrollment metadata |
| `revoked_at` | Set only when `status` is `revoked` |
| `updated_at` | Last enrollment-lifecycle write |

An agent cannot register itself by claiming an `agent_id`. Inserts go through administrator-authenticated control-plane routes.

## Enrollment workflow

`POST /api/v1/targets/{target_id}/agents` requires the `admin` role.

In one transaction the API:

1. Locks the target row (`SELECT FOR UPDATE`).
2. Runs the existing `evaluate_authorization` check.
3. Requires `telemetry.ingest` in the target's stored capabilities.
4. Parses the submitted public key as 32 raw Ed25519 bytes and computes the fingerprint server-side.
5. Inserts the agent (`key_generation = 1`, `status = active`).
6. Appends audit event `agent.enrolled` with the agent id, fingerprint, and generation.

Duplicate agent ids return `agent_already_enrolled`. Duplicate public keys return `public_key_already_registered`. There is no enrollment token, bootstrap secret, or self-service register path.

Viewers can list and read agents. They cannot enroll, rotate, or revoke.

## Public-key binding

The stored hex encoding is lowercase and unique. The fingerprint is not caller-supplied. A later persist call must present the same current public key or it is a `key_mismatch`.

## Target binding

`target_id` is taken from the URL of an existing registry row, not from an arbitrary claim in a telemetry envelope. After enrollment the binding cannot be updated. Telemetry that names a different target is a `target_mismatch`.

## Key lifecycle

- **Initial enrollment:** administrator, eligible target, new key.
- **Rotation:** `POST /api/v1/agents/{agent_id}/rotation` replaces the current public key, increments `key_generation`, and audits `agent.key_rotated` with previous and new fingerprints. Historical `telemetry_events.public_key_hex` values are not rewritten.
- **Revocation:** `POST /api/v1/agents/{agent_id}/revocation` is one-way (`active` → `revoked`). A database trigger rejects restoration. Audit event `agent.revoked`.
- **Rejected keys:** revoked agents and non-current keys cannot store new evidence as enrolled.

Rotation does not invalidate inspection of earlier evidence. Each stored event keeps the public key used to verify that event.

## Identity verification

`evaluate_identity` returns an explicit outcome. It does not collapse failures into a generic success:

| Outcome | Meaning |
|---|---|
| `enrolled` | Agent exists, is active, target matches, current public key matches, target is eligible and grants `telemetry.ingest` |
| `unknown_agent` | No registration for that agent id |
| `revoked_agent` | Agent row is revoked |
| `target_mismatch` | Envelope target is not the bound target |
| `key_mismatch` | Signature key is not the current registered key |
| `inactive_target` | Bound target is missing, revoked, expired, invalid, or lacks `telemetry.ingest` |

Unknown agents remain distinguishable from enrolled agents. Signature verification still runs first and is independent of this table.

## Evidence trust states

`persist_verified_event` always verifies the signature with Phase 2 `verify_event`. It then derives `identity_status`:

| Stored `identity_status` | When |
|---|---|
| `unverified` | Signature verified, agent not registered (`unknown_agent`) |
| `enrolled` | Signature verified and `evaluate_identity` returned `enrolled` |

`revoked_agent`, `target_mismatch`, `key_mismatch`, and `inactive_target` raise `PersistenceError` with that code. No new row is inserted.

The function has no `identity_status` argument. Historical rows are never updated. Events stored before enrollment stay `unverified` and remain readable.

Locking: persist locks the agent row (when present) then the target row, matching other eligibility protection. Revocation waiting on that lock cannot flip the agent mid-insert.

## Historical verification

Inspect stored evidence using the `public_key_hex` on that row, not the agent's current key. After rotation, old events still verify with the old key. After revocation, old events remain in the append-only store.

## Audit

Enrollment lifecycle writes use the existing append-only hash chain:

- `agent.enrolled`
- `agent.key_rotated`
- `agent.revoked`

Payloads contain identifiers and fingerprints, not private keys and not reusable secrets. The chain is a tamper-evident log under the same assumptions as v0.1: the database owner can still disable triggers. It is not a proof that tampering is impossible.

Validation failures (malformed keys, viewer 403, unknown target) are not written as audit events.

## Database

Revision `0004_agent_enrollment` follows `0003_telemetry_events`. It does not edit earlier revisions.

`synapse_app` may `SELECT` and `INSERT` agents, and `UPDATE` only `public_key_hex`, `public_key_fingerprint`, `key_generation`, `status`, `revoked_at`, and `updated_at`. It cannot change `target_id` or enrollment metadata. It still cannot `UPDATE` or `DELETE` `telemetry_events`.

A `BEFORE INSERT` trigger on `telemetry_events` rejects `identity_status = enrolled` unless a matching active agent row exists for that agent id, target, and public key. Target expiry remains an application check under the row lock.

The API process still must not receive `MIGRATION_DATABASE_URL`.

Downgrade restores the Phase 4 `identity_status = 'unverified'` check and drops `agents`. It fails if enrolled evidence rows exist. Downgrade is for laboratory databases, not production history.

## Security assumptions

- Administrator bearer tokens remain the enrollment authority.
- Target eligibility remains fail-closed and evaluated under a row lock.
- Ed25519 public keys are not identities until an administrator binds them.
- `synapse_app` is not the table owner.

## Limitations

- No HTTP telemetry ingestion API
- No collector or network transport
- No enrollment of agents that lack `telemetry.ingest` on the target
- No multi-target agents
- No restoration of a revoked agent
- The migration owner can still disable triggers
- Signature verification is not authorization
