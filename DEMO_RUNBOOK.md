# Synapse-CRS demonstration runbook

This console is an investigation operating environment around the existing FastAPI control plane. It does not execute host actions, does not list raw telemetry events, and does not implement in-memory hotpatching.

## Environment prerequisites

- Python 3.12 virtualenv with `requirements.lock`
- Node.js 22 for the operator console
- PostgreSQL 16 (Docker Compose **or** a local instance)
- A gitignored `.env` copied from `.env.example` (never commit it)
- Do not `source .env` (JSON tokens can be mangled)
- Unset inherited `MIGRATION_DATABASE_URL` / `DATABASE_URL` before `make migrate` / `make api`

## Startup

Preferred (Docker available):

```bash
docker compose --env-file .env -f infra/docker-compose.yml up --build
cd frontend && npm ci && npm run dev
```

Host PostgreSQL (when Docker is unavailable):

```bash
env -u MIGRATION_DATABASE_URL -u DATABASE_URL make migrate
env -u MIGRATION_DATABASE_URL -u DATABASE_URL make api
cd frontend && npm run dev
```

- API: `http://127.0.0.1:8000` (`GET /health`, `GET /ready`)
- Console: `http://127.0.0.1:5173`
- `VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000`

## Authentication (no credentials in this file)

1. Open `/session`.
2. Paste an **admin** bearer from `SYNAPSE_AUTH_TOKENS` in `.env`.
3. Choose **Connect live**.
4. Confirm HUD: `LIVE` or `LAB ENVELOPES`, `API live`, `DB ready`. **DEMO MODE** must disappear.

Viewer tokens can read. They cannot register targets or advance cases (HTTP 403). Invalid tokens must show `UNAVAILABLE` / “Bearer token was rejected” and must **not** load demo fixtures.

## Laboratory data (honesty)

If this environment was seeded with signed envelopes through `POST /api/v1/telemetry/ingest` and a reasoning run with `dataset_label=synthetic_lab`:

- The HUD shows **LAB ENVELOPES**.
- Those rows are stored API evidence. They are **not** `/proc` samples and not independent-dataset evaluation.

## Exact demo sequence

1. **Command Centre (`/`)** — plant meters, intelligence core, target lock, activity tape. Follow **Target → Evidence → Graph → Reasoning**.
2. **Telemetry (`/telemetry`)** — lock the laboratory target; inspect enrolled agent fingerprint; receipt ticker from `finding.supporting_events` only.
3. **Evidence Lab (`/evidence`)** — explorer, relation canvas, inspector, storyline (`observed` / `correlated` / `inferred`).
4. **Investigations (`/investigations/:id`)** — docket, linear states, `executed=false`. ACTION is a stored label.
5. **Threat Graph (`/graph`)** — pan/zoom, kind filters, node inspector. Edges are enrollment, finding support, or stored correlation.
6. **Reasoning (`/reasoning`)** — inspect stages. If selected is `H4_insufficient_evidence`, read the hybrid stage: sparse reconstruction is not treated as malice; engine score is not a probability.
7. **Hypotheses (`/hypotheses`)** — compare support / contradict / unresolved lists from the assessment payload.
8. **Defence (`/defence`)** — SAT/UNSAT/UNKNOWN is a Z3 policy result, not host safety.
9. **Research (`/research`)** — Phases 10–13; independent evaluation **not completed**.
10. **Control (`/control`)** — `GET /audit/verify` `valid=true` and the ledger.

## Screens to show

Command core, Evidence inspector + storyline, full-bleed graph, H4 hybrid readout, Defence solver line, Control chain `valid=true`.

## API endpoints used by the console

`GET /health`, `GET /ready`, `GET /api/v1/targets`, `GET /api/v1/cases`, `GET /api/v1/cases/{id}`, `POST /api/v1/cases/{id}/transitions` (admin), `GET /api/v1/targets/{id}/agents|findings|correlations|risk|reasoning/assessments`, `GET /api/v1/reasoning/assessments/{id}/timeline`, `GET /api/v1/audit/events`, `GET /api/v1/audit/verify`.

There is **no** GET telemetry-events list. Ingest remains `POST /api/v1/telemetry/ingest`.

## 5-minute script

| Time | Say / show |
| --- | --- |
| 0:00 | Command Centre: observer-only control plane. HUD live. Lab envelopes, not /proc. |
| 0:40 | Telemetry: enrollment ≠ continuous monitoring. Ticker is supporting events on findings. |
| 1:20 | Evidence Lab: observed vs correlated vs inferred. Missing evidence stays missing. |
| 2:00 | Graph: only stored relationships. |
| 2:40 | Reasoning: walk stages. H4 means insufficient evidence, not a confirmed attack. Score ≠ probability. |
| 3:20 | Hypotheses + Defence: competing explanations; SAT ≠ real-world safety; nothing is executed. |
| 4:00 | Research: independent CIC-IDS / DMBD evaluation incomplete. |
| 4:30 | Control: audit chain verify. Stop. Do not claim hotpatching. |

## Known limitations

- Independent evaluation on CIC-IDS2017 / DMBD / WinMET / OpTC process trees is **not completed**.
- Laboratory envelopes ≠ genuine endpoint telemetry.
- Autonomous host mitigation is **not** implemented.
- In-memory hotpatching is **not** implemented (the product name is not evidence).
- Tiny synthetic fixtures are not generalizable detection rates.
- Case ACTION does not change a host (`executed` remains false).
- Console snapshot uses the first page of each list (`limit=100`).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| API refused | `curl /health`; uvicorn on 8000; CORS origin `http://127.0.0.1:5173` |
| `/ready` not ready | PostgreSQL; `DATABASE_URL` as `synapse_app` |
| API will not start | `MIGRATION_DATABASE_URL` must be **unset** in the API process |
| Alembic migrated the wrong database | Unset inherited `MIGRATION_DATABASE_URL` so `.env` is used |
| Auth rejected | Token must match `SYNAPSE_AUTH_TOKENS`; ≥16 characters |
| Demo rows after a live failure | Bug — live errors must stay empty. Sign out and report |
| Empty live snapshot | Admin has not registered a target yet |

## Claims that must not be made

- Zero-day detection, causal inference from ablation, or production accuracy
- Continuous monitoring solely because an agent is enrolled
- SAT as proof a host is safe
- Automatic mitigation or live patching
- Independent dataset success when reports say `not_completed`
- That laboratory envelopes are `/proc` telemetry
