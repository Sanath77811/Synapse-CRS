# Architecture

v0.1 is a modular monolith. One FastAPI process is the composition root. Domain rules live in importable packages so they can fail tests before they are wired to HTTP.

```text
Operator
  |  bearer token
  v
FastAPI  ---- PostgreSQL
  |            targets
  |            cases
  |            case_transitions
  |            audit_events        (append-only)
  |            audit_chain_state   (mutable counter)
  |
  +-- packages/contracts
  +-- packages/policy
  +-- packages/cases
  +-- packages/audit
```

There is no agent, telemetry bus, evidence runner, model client, solver, or mitigation executor in this version.

## Request path

1. The process refuses to start when `DATABASE_URL` or `SYNAPSE_AUTH_TOKENS` is missing or unsafe.
2. `/health` does not touch the database. `/ready` runs `SELECT 1`.
3. `/api/v1/*` requires a bearer token. The actor name stored in audit events comes from the token record, not from the request body.
4. Writes require the `admin` role. Reads accept `admin` or `viewer`.
5. Creating a target rejects a past expiry, an unknown capability, and a scope outside `lab` or `development`.
6. Opening or advancing a case loads the target and runs `evaluate_authorization`. Any failed check returns 409 and leaves the case unchanged.
7. A transition updates `cases.state`, inserts `case_transitions`, and appends an audit event whose payload sets `executed` to false.
8. The audit append locks `audit_chain_state`, hashes the previous head, and stores the new head in the same transaction as the business write.

## Case states

```text
AUTHORIZED_TARGET
  -> OBSERVATION
  -> EVIDENCE
  -> HYPOTHESIS
  -> VERIFICATION
  -> APPROVAL
  -> ACTION
  -> VALIDATION
  -> ROLLBACK
  -> SEALED_AUDIT
```

`SEALED_AUDIT` is terminal. v0.1 does not model cancellation or rollback from an earlier state. Entering `ACTION` does not perform an action.

## Data ownership

| Table | Purpose | Who may change it through the app role |
| --- | --- | --- |
| `targets` | Registry and authorization | Insert and update |
| `cases` | Current pipeline state | Insert and update |
| `case_transitions` | Transition history | Insert |
| `audit_events` | Hash-chained history | Insert |
| `audit_chain_state` | Next sequence and head hash | Update of the single bookkeeping row |

The API does not expose delete routes for these tables.

## Contracts

`schemas/*.schema.json` is contract version `1.0.0`. Pydantic models in `packages/contracts` are the runtime validators. Tests check that published examples satisfy both.
