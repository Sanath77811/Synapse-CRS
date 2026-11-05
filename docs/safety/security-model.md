# Security model

## Fail closed

- Missing configuration prevents startup.
- Missing or unknown bearer tokens return 401.
- A known token with the wrong role returns 403.
- Invalid input returns 422 and is not stored.
- An ineligible target returns 409. Case state does not change.
- An illegal transition returns 409. Case state does not change.
- If the audit insert fails, the surrounding transaction rolls back the business write.
- `/ready` returns 503 when PostgreSQL cannot answer `SELECT 1`, without including the driver error in the response.
- Unexpected exceptions return a fixed 500 body. Logs record the exception type only.

## Least privilege

Compose creates `synapse_app`. A one-shot `migrate` service runs Alembic as the PostgreSQL superuser defined by `POSTGRES_USER`. The API process receives only `DATABASE_URL` and connects as `synapse_app`. It refuses to start when `MIGRATION_DATABASE_URL` is set.

| Role | Granted in v0.1 |
| --- | --- |
| `synapse_app` | `SELECT`, `INSERT` on `targets` and `cases`; `UPDATE` of `authorization_status` and `updated_at` on `targets`; `UPDATE` of `state` and `updated_at` on `cases`; `SELECT`, `INSERT` on `case_transitions`; `SELECT`, `INSERT` on `audit_events`; `SELECT`, `UPDATE` on `audit_chain_state` |
| Migration user | Table owner. Required to create schema and, in tests, to truncate fixtures. Not present in the API process |

Triggers reject any authorization change other than `active` to `revoked`, a case insert whose state is not `AUTHORIZED_TARGET`, and a case update that is not the next state in the linear pipeline. Migration `0002_enforce_state` fails if `synapse_app` does not already exist. Start PostgreSQL (so `infra/postgres/init-roles.sh` runs) before the migrate service. Tests create the role themselves when it is absent.

## Authentication

`SYNAPSE_AUTH_TOKENS` is a JSON object:

```json
{
  "replace-with-a-long-random-token": {"actor": "local-admin", "role": "admin"}
}
```

Comparison uses SHA-256 digests and `hmac.compare_digest`. Tokens are not written to audit payloads. Production mode rejects tokens shorter than 32 characters.

This is a local operator boundary, not a multi-tenant identity system. A separate approver role is deferred until a version exists that can apply a change.

## Scope and capabilities

Scope environment must be `lab` or `development`. Assets are bounded identifiers. The strings `*`, `0.0.0.0`, and `::` are rejected. The API never dials an asset name.

Allowed capability names:

- `telemetry.ingest`
- `evidence.submit`
- `reasoning.request`
- `verification.request`

`shell.execute`, `mitigation.apply`, and any other name are rejected. Adding a name later has to be an explicit contract change.

## Secrets

Passwords, tokens, and database URLs come from the environment or from a gitignored `.env`. The Compose file interpolates variables. The image does not copy `.env`. CI uses passwords that exist only for the ephemeral database in that workflow, and tests replace the bearer token with a random value for the pytest process.

## Human gate

v0.1 has no mitigation to approve. The admin role is still required to move a case, including into `APPROVAL` and `ACTION`, so an unattended viewer cannot invent pipeline progress.
