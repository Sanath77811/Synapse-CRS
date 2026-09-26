# Synapse-CRS

Autonomous Runtime Cyber Defense and Formal Verification Platform.

Project currently under active development.

Synapse-CRS is a research and startup platform aimed at autonomous runtime cyber defense on systems we own or are explicitly authorized to test. **Version 0.1 is the control-plane foundation only.** It registers targets, records authorization, stores case state, and appends audit events. It does not observe hosts, analyze vulnerabilities, call a model, prove properties, or change a running system.

The short project statement above is the goal. It is not a description of what this repository can do today. See [docs/safety/claims.md](docs/safety/claims.md).

## Current capabilities

- FastAPI control plane with OpenAPI documentation at `/docs` when `SYNAPSE_ENVIRONMENT` is not `production`.
- PostgreSQL schema and Alembic migrations, including a separate `synapse_app` database role.
- Target registry: owner, scope, authorization status, expiry, and an allowlist of capability names.
- Fail-closed eligibility checks. Expired, revoked, or invalid targets cannot open or advance a case.
- Case pipeline state machine. Transitions are stored. Nothing is executed.
- Append-only audit events with a SHA-256 hash chain.
- Bearer-token authentication and an admin/viewer role split.
- pytest suite, ruff, Docker Compose, and GitHub Actions.

## Explicit non-goals of v0.1

- Zero-day or unknown-vulnerability discovery
- Automatic or manual exploitation
- Automatic binary patching or hotpatching
- Zero-downtime remediation
- Mathematical proof of system security
- eBPF, Z3, NetworkX, or a runtime agent
- Connections to registered targets

## Repository layout

```text
apps/api/          FastAPI control plane and Alembic migrations
packages/contracts Versioned pydantic models
packages/policy    Target eligibility decisions
packages/cases     Case transition rules
packages/audit     Hash-chain helpers
frontend/          Minimal React status page
agent/             Placeholder. The lab agent starts in v0.2.
schemas/           JSON Schema 2020-12 contracts, version 1.0.0
tests/             Unit tests and PostgreSQL integration tests
docs/              Architecture, threat model, decisions, safety, roadmap
infra/             Docker Compose, Postgres init, API image
```

`packages/cases` is an addition to the requested layout. Transition rules are pure functions and are tested without HTTP or PostgreSQL. Keeping them out of `packages/policy` avoids mixing authorization with the pipeline state machine. See [docs/decisions/0001-package-layout.md](docs/decisions/0001-package-layout.md).

The earlier `readme.md` filename collided with `README.md` on case-insensitive filesystems. Its text is preserved at the top of this file.

## Local setup

Requirements: Docker with Compose, Python 3.12, and Node.js 22 if you want the status page.

```bash
cp .env.example .env
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_hex(24)); print('SYNAPSE_APP_PASSWORD=' + secrets.token_hex(24))"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Edit `.env`:

- Set `POSTGRES_PASSWORD` and `SYNAPSE_APP_PASSWORD` to the generated values. Passwords must match `[A-Za-z0-9_-]{16,128}`.
- Put those passwords into `MIGRATION_DATABASE_URL` and `DATABASE_URL`.
- Set `SYNAPSE_AUTH_TOKENS` to one line of JSON with an admin token and a viewer token. Each token must be at least 16 characters. Use a distinct `actor` for each token.

Start PostgreSQL and the API:

```bash
docker compose --env-file .env -f infra/docker-compose.yml up --build
```

The API listens on `127.0.0.1:8000`. PostgreSQL listens on `127.0.0.1:5432`.

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/ready
```

`/ready` reports PostgreSQL connectivity. Compose runs migrations in a one-shot `migrate` service, then starts the API. The API process receives `DATABASE_URL` for `synapse_app` and refuses to start if `MIGRATION_DATABASE_URL` is set.

Host-side tests and lint, against a `synapse_test` database on that Postgres instance:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

`make install`, `make test`, and `make lint` wrap the same commands. pytest, the API, and Alembic read `.env` directly and then point the test suite at `synapse_test` so it does not truncate the development database. Do not `source .env`; a shell will mangle the token JSON.

Status page:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The page reads `/health` and `/ready` only.

More detail: [docs/development/workflow.md](docs/development/workflow.md).

## Security model

Operators authenticate with bearer tokens supplied through `SYNAPSE_AUTH_TOKENS`. The application does not contain credentials. Viewers can read. Admins can register, revoke, and advance case state. Every case change locks the target row and re-checks eligibility. Revocation is one-way in the database, and a case row can move only along the legal transition path. Audit rows are inserted by `synapse_app` and cannot be updated, deleted, or truncated with that role. A database owner can still disable triggers; that limit is stated in [docs/safety/claims.md](docs/safety/claims.md) and [docs/threat-model/threat-model.md](docs/threat-model/threat-model.md).

## Development workflow

1. Write or update the spec in `docs/` before changing a subsystem.
2. Keep stage logic in a package so it can be tested without the API.
3. Run unit tests, then the PostgreSQL integration tests.
4. Run ruff.
5. Do not start the next research stage in the same change as an unfinished foundation fix.

v0.1 acceptance criteria: [docs/development/v0.1-acceptance.md](docs/development/v0.1-acceptance.md).

## Roadmap

v0.2 through v0.8 are research stages, not commitments that each stage will succeed. [docs/roadmap.md](docs/roadmap.md).

## License

No license has been selected.
