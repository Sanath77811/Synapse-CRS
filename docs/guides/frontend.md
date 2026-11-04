# Synapse-CRS operator console

The React console is an investigation operating environment around the existing FastAPI control plane. It does not add API routes, does not execute host actions, and does not invent a telemetry-events list endpoint.

## Architecture

- React 19, TypeScript, Vite, React Router.
- Session: `sessionStorage` bearer token + `demo`/`live` mode (`frontend/src/auth/session.ts`).
- Snapshot: `usePlatform` loads demo fixtures **or** live paginated GETs. Live failures leave empty live state; they do not silently swap in demo rows.
- API client: `frontend/src/api/client.ts` (`VITE_API_BASE_URL`, 12s timeout, AbortSignal, 401/403/404/422 mapping). Tokens are never logged.
- Workspaces live under `frontend/src/pages/`. Threat Graph is lazy-loaded.
- Graph nodes are derived in `graphFromSnapshot` from targets, enrolled agents, findings, supporting events, and stored correlation links.

## Design system

Tokens live in `frontend/src/styles.css` (`--void`, `--hud`, `--cyan`, `--blue`, `--violet`, `--amber`, `--red`, `--sans`, `--mono`, `--rail`). Each workspace uses a distinct composition (command grid, forensic tri-pane, full-viewport graph, reasoning theatre, investigation dossier).

## Routes

| Path | Workspace |
| --- | --- |
| `/` | Command Centre |
| `/telemetry` | Telemetry Operations |
| `/evidence` | Evidence Lab |
| `/investigations`, `/investigations/:caseId` | Investigation Studio |
| `/graph` | Threat Graph |
| `/reasoning` | Reasoning Engine |
| `/hypotheses` | Hypothesis Arena |
| `/defence` | Defence Lab |
| `/research`, `/research/:phaseId` | Research Observatory |
| `/control` | System Control |
| `/session` | Bearer session |

Ctrl/Cmd+K opens the command palette (navigate, open a loaded target/case, refresh, enter demo).

## Commands

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Default session is **DEMO MODE** (synthetic lab records). Connect a live bearer token at `/session`.

Production build and tests:

```bash
cd frontend
npm test
npm run build
```

Backend (separate process). Copy `.env.example` to `.env` (gitignored) and fill passwords/tokens as in the README. Do not commit `.env`. Do not `source .env` (the token JSON can be mangled). Do not start the API while `MIGRATION_DATABASE_URL` is in the process environment.

```bash
# Preferred: Compose (Postgres + migrate + API)
docker compose --env-file .env -f infra/docker-compose.yml up --build

# Host-side API against an already-running local Postgres (this environment
# had Docker unavailable; PostgreSQL 16 on 127.0.0.1:5432 was used instead):
env -u MIGRATION_DATABASE_URL -u DATABASE_URL make migrate
env -u MIGRATION_DATABASE_URL -u DATABASE_URL make api
```

`make migrate` applies Alembic to the database named by `.env`. Unset any inherited `MIGRATION_DATABASE_URL` so the file is not ignored.

`VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000`. CORS must include the Vite origin (`http://127.0.0.1:5173`). Error bodies from FastAPI are `{ "error": { "code", "message", "details" } }`; the console reads that envelope.

## Integrated live endpoints

Authenticated GETs used by the console:

- `/health`, `/ready`
- `GET /api/v1/targets`
- `GET /api/v1/cases`, `GET /api/v1/cases/{id}`
- `POST /api/v1/cases/{id}/transitions` (admin; stores pipeline state only)
- `GET /api/v1/targets/{id}/agents`
- `GET /api/v1/targets/{id}/findings`
- `GET /api/v1/targets/{id}/correlations`
- `GET /api/v1/targets/{id}/risk`
- `GET /api/v1/targets/{id}/reasoning/assessments`
- `GET /api/v1/reasoning/assessments/{id}/timeline`
- `GET /api/v1/audit/events`
- `GET /api/v1/audit/verify`

Not used as a list UI (no such GET): telemetry event dump. Ingest remains `POST /api/v1/telemetry/ingest`.

## Demonstration path

1. Command Centre — plant meters, intelligence core, activity tape.
2. Telemetry Operations — lock a target; inspect enrollment vs supporting-event ticker.
3. Evidence Lab — explorer, relation canvas, inspector, storyline.
4. Investigation Studio — docket, linear state track, ACTIVITY vs ACTION honesty.
5. Threat Graph — pan/zoom/fit, kind filters, node inspector.
6. Reasoning Engine — inspect stages; scores are not probabilities.
7. Hypothesis Arena — competing explanations from the stored assessment.
8. Defence Lab — SAT/UNSAT/UNKNOWN is policy verification, not host safety.
9. Research Observatory — phase notebooks; independent validation not completed.
10. System Control — health, audit ledger, chain verify.

## Honesty rules

- Demo records are labelled. They are not enrolled telemetry.
- Live API errors show empty live state plus an error, not demo substitution.
- There is no list-telemetry HTTP endpoint; supporting events come from findings.
- Case ACTION does not run a mitigation (`executed` remains false).
- Research pages copy repository conclusions, including fail-closed dataset status.
- Formal SAT does not prove real-world host safety.
