# Telemetry ingestion API

`POST /api/v1/telemetry/ingest` is the first network-facing telemetry intake. It is an ingestion API, not a live collector. It does not read `/proc`, open sockets to targets, reason about threats, or apply mitigations.

Only an administrator-enrolled agent may submit accepted events. A valid Ed25519 signature proves possession of a private key. It does not enroll an agent and it does not authorize a target.

## Endpoint and request format

```http
POST /api/v1/telemetry/ingest
Content-Type: application/json
Content-Length: <bytes>
```

The request is not authenticated with a bearer token. Agent authentication is the detached signature over the Phase 1 envelope, checked against the **registered** public key. Administrator enrollment, rotation, and revocation remain on the existing bearer-protected routes.

```json
{
  "envelope": { "...Phase 1 telemetry envelope..." },
  "signature": "<88-character standard Base64 Ed25519 signature>"
}
```

Unknown fields are rejected. The signature is not a field of the envelope. Callers must not send `verified`, `identity_status`, `authorized`, `agent_enrolled`, `trust_level`, or a public key.

The envelope must already satisfy the Phase 1 contract. The server does not re-normalize observations (normalization would change the signed bytes).

## Response format

New evidence: HTTP **201**. Exact duplicate: HTTP **200**.

```json
{
  "event_id": "uuid",
  "persistence_status": "stored",
  "signature_verified": true,
  "identity_status": "enrolled",
  "event_type": "process_started",
  "agent_id": "uuid",
  "target_id": "uuid",
  "received_at": "2026-09-29T17:34:00.000000Z",
  "contract_version": "1.0.0"
}
```

Successful HTTP ingest always reports `identity_status=enrolled`. The response does not include the envelope, signature, or public key.

Errors use the existing `{ "error": { "code", "message", "details" } }` envelope. Messages are fixed. They do not include SQL, stack traces, DSNs, signatures, or private keys.

## Verification pipeline

1. Content-Length present and within `SYNAPSE_MAX_REQUEST_BYTES` (default 65536, range 4096–1048576).
2. `Content-Type` is `application/json` (optional charset parameter ignored).
3. Strict request model validation, including Phase 1 envelope validation.
4. Signature decoding (standard Base64, 64 bytes).
5. Agent row lock and lookup by `envelope.agent_id`.
6. Load the **registered** public key from that row. The request cannot supply a key.
7. `persist_verified_event`, which runs `verify_event` and `evaluate_identity` under the existing agent-then-target locks, then inserts.

The HTTP layer rejects `unknown_agent` **before** persist. The Phase 4 service may still store unknown-agent evidence as `unverified` when called directly. Network ingest does not.

## Identity authorization

| Outcome | HTTP | Notes |
|---|---|---|
| enrolled + stored | 201 | Accepted |
| enrolled + duplicate | 200 | Idempotent exact duplicate |
| unknown_agent | 403 | Not enrolled; no evidence row |
| revoked_agent | 403 | No new row |
| target_mismatch | 403 | No new row |
| key_mismatch | 403 | Registered key changed under the lock |
| inactive_target | 409 | Revoked, expired, invalid, or missing `telemetry.ingest` |
| invalid_signature | 401 | Tamper or signed with a key that is not current |
| invalid_envelope | 422 | Schema or request model |
| event_id_conflict / sequence_conflict | 409 | Different evidence, existing row unchanged |

Unknown agents are not treated as enrolled.

## Duplicate handling

Reuse Phase 4 uniqueness: `event_id` and `(agent_id, boot_id, sequence)`.

- Exact duplicate: 200, `persistence_status=duplicate`, no second row.
- Same event id, different bytes: 409 `event_id_conflict`.
- Same agent/boot/sequence, different event id: 409 `sequence_conflict`.

Uniqueness detects duplicates of stored evidence. It is not a complete freshness or anti-replay policy (no nonce window, no timestamp skew bound, no per-agent rate limit).

## Request limits and abuse safeguards

- Maximum body size via `SYNAPSE_MAX_REQUEST_BYTES`.
- POST/PUT/PATCH without `Content-Length` returns 411.
- Ingest without JSON content type returns 415.
- Strict pydantic models; no unknown fields; Phase 1 already bounds strings and integers.
- No raw request-body logging. No signature or private-key logging.
- No Redis or process-local request-rate limiter. Multi-worker production would not share in-memory counters. Size limits are the abuse control in this phase.

## Audit

Same append-only hash chain as v0.1:

- `telemetry.ingested`
- `telemetry.duplicate`
- `telemetry.rejected` with a reason code, agent id, and event id

Payloads omit envelopes, signatures, keys, and process observations. Actor is `telemetry-ingest`. If the claimed target is not in the registry, `target_id` on the audit row is null so the existing foreign key still holds.

The chain remains tamper-evident under the same limitation as v0.1: the database owner can disable triggers.

Rejection audits are written in the same request transaction as the HTTP error response so they persist when the session commits.

## Database transactions and concurrency

Ingest locks the agent row, then `persist_verified_event` locks the agent again and the target, then inserts evidence, then appends audit. Revocation and rotation also lock the agent first. A persist that observed `enrolled` holds those locks until commit, so a concurrent revoke cannot mark the in-flight row enrolled after the agent became ineligible.

Exact concurrent duplicates: one insert wins; the other is classified as `duplicate`.

## Health

Existing `/health` (liveness) and `/ready` (PostgreSQL `SELECT 1`) are unchanged. Ingest does not add another probe.

## HTTPS deployment

This API process serves HTTP. Production must terminate TLS at a reverse proxy or load balancer and forward to the process only on a private interface. The development server does not provide HTTPS. Trusted-proxy headers are not interpreted; the API does not reconstruct client scheme from `X-Forwarded-Proto`.

Bind as in Compose: `127.0.0.1:8000` unless an operator-controlled proxy is in front.

## Local tests

```bash
.venv/bin/pytest tests/integration/test_telemetry_ingest.py
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Integration tests use the existing `synapse_test` database and `synapse_app` role.

## Limitations

- Not a collector and not an agent transport client
- No distributed rate limiting
- No request-body streaming limit beyond Content-Length (chunked POST without length is rejected)
- Duplicate detection is not a full replay policy
- Signature verification is not enrollment
- No threat reasoning or mitigation
- HTTPS is a deployment requirement, not a property of the Python process
