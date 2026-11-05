# Production deployment (Vercel + Render + managed PostgreSQL)

Observer-only control plane. Do not seed synthetic laboratory envelopes into production. Do not put tokens in Vercel env vars.

## Deploy this git ref

- Branch: `cursor/v0.2-telemetry-2464`
- Do **not** deploy `main` (README only).
- PR #2 is merged into `cursor/v0.1-security-hardening-2464`, not `main`.
- Push this branch after the Docker `PORT` / `PYTHONPATH` fixes, then pin the commit shown in `git log -1`.

## Who must log in (this agent cannot)

| Service | Where |
| --- | --- |
| Vercel | https://vercel.com/login then import `Sanath77811/Synapse-CRS` |
| Render | https://dashboard.render.com then New → Web Service from the same GitHub repo |
| PostgreSQL | Your chosen managed provider dashboard (Render Postgres is paid; Neon/Supabase have free tiers if you prefer). This agent will not create paid databases. |

There is no Vercel or Render CLI session in this environment. Deployment is **not** complete until you finish those dashboards.

## Exact commands

Frontend (Vercel Root Directory = `frontend`):

```bash
cd frontend && npm ci && npm test && npm run build
```

Output: `frontend/dist`.

Backend image start (what the container runs):

```text
uvicorn synapse_api.main:app --host 0.0.0.0 --port $PORT
```

`$PORT` is injected by Render. Do not bind `127.0.0.1`.

Migrations (owner DSN, **separate** from the web process):

```bash
MIGRATION_DATABASE_URL='postgresql+psycopg://OWNER:PASSWORD@HOST:5432/DB?sslmode=require' \
  alembic -c apps/api/alembic.ini upgrade head
```

Never set `MIGRATION_DATABASE_URL` on the Render **web** service. `create_app` refuses to start if it is present.

## Required environment variables

### Render web service (secrets)

| Name | Notes |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://synapse_app:...@host:5432/db?sslmode=require` |
| `SYNAPSE_ENVIRONMENT` | `production` (tokens must be ≥32 characters) |
| `SYNAPSE_AUTH_TOKENS` | One-line JSON, unique actors, admin + viewer. Dashboard secret only. |
| `SYNAPSE_CORS_ORIGINS` | Exact Vercel origin(s), comma-separated, **no** `*` |
| `SYNAPSE_MAX_REQUEST_BYTES` | Optional, default 65536 |

### Render one-off migrate shell only

| Name | Notes |
| --- | --- |
| `MIGRATION_DATABASE_URL` | Owner DSN, same `postgresql+psycopg://...?sslmode=require` shape |

### Vercel (Project → Settings → Environment Variables)

| Name | Notes |
| --- | --- |
| `VITE_API_BASE_URL` | `https://<render-service>.onrender.com` with **no** trailing slash. Baked in at **build** time. |

Do **not** add `SYNAPSE_AUTH_TOKENS`, `DATABASE_URL`, or passwords to Vercel.

## Operator steps (order)

1. Approve a **managed PostgreSQL** plan if it is paid. Create an empty database. Do not restore synthetic lab dumps.
2. As owner, run `infra/deploy/bootstrap-synapse-app.sql` (real password, real database name).
3. In Render: New Web Service, repo `Synapse-CRS`, branch `cursor/v0.2-telemetry-2464`, Docker, Dockerfile `infra/docker/api.Dockerfile`, health check `/health`. Instance: start with free/starter only if you approved it; sklearn + Z3 may need more RAM.
4. Set Render secrets listed above. For CORS, you can temporarily use the production Vercel URL you will choose (for example `https://<project>.vercel.app`).
5. Open Render Shell **once**, export `MIGRATION_DATABASE_URL` only in that session, run Alembic, then close the shell. Confirm `GET /health` and `GET /ready` on the public API URL.
6. In Vercel: Import repo, **Production Branch** `cursor/v0.2-telemetry-2464` (never `main` — `main` is README-only and 404s). **Root Directory** `frontend`. Output Directory **`dist`** (not `frontend/dist`). Node 22. Env `VITE_API_BASE_URL` = the Render origin. Deploy Production. If Root Directory is left empty, repo-root `vercel.json` still builds `frontend/dist` on this branch.
7. Copy the exact Production origin from Vercel (scheme + host, no path). Set `SYNAPSE_CORS_ORIGINS` on Render to that value. Redeploy or restart the API.
8. Open the Vercel URL, use **Connect live** with an admin token you generated locally. Confirm HUD is not DEMO MODE. Do **not** ingest `synthetic_lab` envelopes into this database.

## Chicken-and-egg

Render needs the Vercel origin for CORS. Vercel needs the Render origin for `VITE_API_BASE_URL`. Deploy API first, then frontend, then tighten CORS and restart API. If you change the Render URL, rebuild Vercel.

## What this deployment is not

- Not a fleet EDR.
- Empty findings are expected until you enroll a real agent against an owned lab/development target.
- `/docs` is disabled when `SYNAPSE_ENVIRONMENT=production`.
