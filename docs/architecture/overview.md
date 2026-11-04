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
  |            agents              (enrolled identities)
  |            telemetry_events    (append-only evidence)
  |
  +-- packages/contracts
  +-- packages/policy
  +-- packages/cases
  +-- packages/audit
  +-- packages/telemetry
  +-- packages/agent
  +-- packages/correlation
  +-- packages/reasoning
  +-- packages/validation
```

Enrolled agents may POST signed telemetry to `/api/v1/telemetry/ingest`. The Linux collector in `packages/agent` polls procfs and uses that endpoint. `packages/correlation` links stored enrolled evidence into explainable findings. `packages/reasoning` reconstructs timelines, scores a synthetic Isolation Forest baseline, evaluates inspectable rules, and Z3-checks recommendation records. `packages/validation` runs offline research experiments (Phase 10 synthetic reconstructions, Phase 11 flow benchmarks, Phase 12 endpoint adapters); it does not write benchmark rows into `telemetry_events`. There is no mitigation executor.

## Request path

1. The process refuses to start when `DATABASE_URL` or `SYNAPSE_AUTH_TOKENS` is missing or unsafe.
2. `/health` does not touch the database. `/ready` runs `SELECT 1`.
3. Control-plane `/api/v1/*` routes require a bearer token. Telemetry ingest authenticates with a detached signature against the enrolled public key. The actor name stored in control-plane audit events comes from the token record, not from the request body.
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
| `agents` | Enrolled agent identity, public key, target binding | Insert and enrollment-lifecycle update |
| `telemetry_events` | Signed telemetry evidence | Insert only |
| `correlation_runs` | Correlation execution records | Insert |
| `correlation_links` | Derived event relationships | Insert |
| `findings` | Deduplicated explainable findings | Insert and update of derived fields |

The API does not expose delete routes for these tables.

## Contracts

`schemas/*.schema.json` is contract version `1.0.0`. Pydantic models in `packages/contracts` are the runtime validators. Tests check that published examples satisfy both.
