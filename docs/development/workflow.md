# Development workflow

## Environment

Use Python 3.12, Docker Compose, and Node.js 22 for the status page. Install Python dependencies from `requirements.lock` so local runs match CI.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
```

Copy `.env.example` to `.env` and fill it in before Compose or pytest. See the README for the password and token generation commands.

## Make targets

| Command | Effect |
| --- | --- |
| `make install` | Create `.venv` and install the lock file |
| `make test` | Run pytest |
| `make lint` | Run ruff check and format check |
| `make format` | Apply ruff fixes and formatting |
| `make api` | Run uvicorn on `127.0.0.1:8000` using the host `.env` |
| `make migrate` | Apply Alembic migrations with `MIGRATION_DATABASE_URL` or `DATABASE_URL` |

`make api` and `make migrate` read `.env` directly. Do not `source .env` in a shell: the token JSON can be altered by the shell parser. pytest also loads `.env` when the variables are unset.

## What to run before a change is finished

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
```

Unit tests in `tests/unit` do not need PostgreSQL. The full suite does. Integration tests create or reuse `synapse_test` and a `synapse_app` role. They do not truncate the `synapse` development database.

Reset local data when the application role password changes:

```bash
docker compose --env-file .env -f infra/docker-compose.yml down -v
docker compose --env-file .env -f infra/docker-compose.yml up --build
```

The Postgres init script runs only on a new volume.

## Review rule

Each package should stay testable without the process next to it:

- Contract changes update `schemas/` and `tests/fixtures/contracts/`.
- Eligibility changes land in `packages/policy` with unit tests.
- Transition changes land in `packages/cases` with unit tests.
- Hash changes land in `packages/audit` with unit tests.
- HTTP and SQL changes land with an integration test.

Do not add a shell, a raw command route, or a client that connects to a target as part of foundation work.

## CI

`.github/workflows/ci.yml` installs the lock file, runs ruff and pytest against a PostgreSQL service, and builds the frontend. The workflow database password is a CI fixture. Do not reuse it anywhere else.
