# Linux agent demonstration

The demo starts the existing API in-process, enrolls an agent with the administrator token from `.env`, polls this machine's `/proc`, delivers signed events, then checks PostgreSQL. It also sends a tampered signature and an unregistered agent id.

It uses only the local authorized development database. It does not scan other hosts.

## Command

PostgreSQL must already be listening on `127.0.0.1:5432` with `.env` populated (same values as pytest).

```bash
make demo-agent
```

or

```bash
.venv/bin/python -m synapse_agent.demo
```

The demo binds the API at `127.0.0.1:18080` so it does not clash with a developer server on port 8000. It pops `MIGRATION_DATABASE_URL` before `create_app`.

## What it does

1. Migrates the database if a migration URL is present.
2. Starts FastAPI.
3. Creates a lab target with `telemetry.ingest`.
4. Writes a local Ed25519 key and enrolls that public key.
5. Forks a short-lived child and GETs `/health` so procfs shows process and network rows.
6. Runs a few collector cycles and POSTs to ingest.
7. Queries `telemetry_events` for `identity_status=enrolled`.
8. POSTs a tampered signature (expects 401) and an unknown agent (expects 403).

Stderr JSON line `demo_complete` reports accepted event counts and those HTTP statuses. Exit code 0 means those checks passed.

## Limitations

The child and `/health` GET are laboratory stimuli. Polling can miss short-lived work. The demo is not a performance benchmark.
