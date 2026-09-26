# Threat model

## System under consideration

Synapse-CRS v0.1 is a local control plane: a FastAPI process, a PostgreSQL database, and a static status page. It stores authorization decisions about owned lab and development assets. It does not connect to those assets.

## Assets

- Bearer tokens and database passwords
- Target ownership, scope, and expiry
- Case state, which later versions may treat as authority to act
- The audit trail

## Actors

| Actor | Trust |
| --- | --- |
| Admin operator | May register, revoke, and advance cases |
| Viewer | May read registry, cases, and audit |
| `synapse_app` database role | May insert audit events and update chain bookkeeping. May not update or delete audit events |
| Migration role | Owns tables, runs Alembic, and can disable triggers |
| Unauthenticated caller | May call `/health`, `/ready`, and `/` only |
| External network peer | Not a client this version contacts |

## Assumptions

- v0.1 is bound to localhost in Compose and is not an internet service.
- Operators protect `.env`.
- PostgreSQL is the one reached through `DATABASE_URL`, on a machine the operator controls.
- Tokens are random and are not committed.

## In scope

| Threat | Control |
| --- | --- |
| Unauthenticated use of the registry | Bearer token required. Empty token configuration prevents process start |
| Viewer performs a write | Admin role required. Failure is 403 |
| Caller supplies an audit actor | Actor is taken from the token record. Extra JSON fields are rejected |
| Expired or revoked target proceeds toward a later action | Eligibility is re-checked on case create and on every transition. Failure is 409 and the row is unchanged |
| Over-broad scope or unknown capability | Request validation rejects the write before insert |
| Ordinary application update or delete of an audit event | Privileges omit update and delete. Triggers raise `audit_events are append-only` for the table owner as well |
| Error response echoes a token or SQL exception | Validation errors omit the authorization header. Database failures return a fixed message |
| Production boot with a short token | `SYNAPSE_ENVIRONMENT=production` requires 32-character tokens and disables `/docs` |
| Wildcard browser origin | `SYNAPSE_CORS_ORIGINS=*` is rejected at startup |

## Out of scope for v0.1

- A hostile database superuser, container escape, or stolen disk. The hash chain makes some edits detectable. It does not stop an owner from disabling triggers, dropping the table, or rewriting backups.
- Token theft from a developer workstation.
- Availability attacks against the API.
- Compromise of a future agent. No agent ships in this version.
- Proof that a registered asset is actually owned by the named operator. The registry records the claim. It does not verify it.

## Residual risk

An operator who can run migrations can rewrite history. A later version can anchor the head hash outside the database. Until that exists, audit integrity depends on database access control and on operators noticing a failed `/api/v1/audit/verify` result.
