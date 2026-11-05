# Documentation validation report

Generated from repository inspection plus the files in `docs/presentation_package/`.  
Root archive: `SYNAPSE_CRS_COMPLETE_PRESENTATION_PACKAGE.zip` (PDFs, Markdown manuals, fact sheet, this report).

## Deliverable inventory

| File | Present | Notes |
| --- | --- | --- |
| `SYNAPSE_CRS_COMPLETE_USER_AND_TECHNICAL_GUIDE.pdf` | yes | 19 pages |
| `SYNAPSE_CRS_PRESENTATION_MASTER_HANDBOOK.pdf` | yes | 29 pages |
| `SYNAPSE_CRS_100_VIVA_QUESTIONS_AND_ANSWERS.pdf` | yes | 38 pages |
| matching `.md` for each of the three | yes | |
| `IMPLEMENTATION_FACT_SHEET.md` | yes | |
| `DOCUMENTATION_VALIDATION_REPORT.md` | yes | this file |
| `README.md` | yes | how to use the pack |
| `SYNAPSE_CRS_COMPLETE_PRESENTATION_PACKAGE.zip` | yes | repository root |

Ancillary generators (not required by the brief): `_viva_questions.py`, `_render_pdfs.py`, print `.html`.

PDFs open with `pypdf.PdfReader` (no decrypt, extractable text on page 1 of each). Chrome headless printed from HTML; headers/footers/page numbers stamped with ReportLab.

## Source inspection

Inspected:

- `apps/api/src/synapse_api/routers/*.py` and `main.py` (`GET /`, health, targets, agents, cases, audit, telemetry ingest, correlation, reasoning).
- SQLAlchemy models + Alembic `0001`–`0006`.
- `packages/{contracts,policy,cases,audit,telemetry,agent,correlation,reasoning,validation}`.
- `frontend/src/App.tsx` routes and workspace pages.
- Tests under `tests/` and frontend vitest (referenced, not re-run in this documentation pass).
- `docs/safety/claims.md`, `docs/architecture/*`, `docs/research/benchmark-results.md`, `README.md`, `DEMO_RUNBOOK.md`.

**Presentation sources:** no `.ppt`, `.pptx`, or project presentation `.pdf` in the repository. Handbook uses a **suggested 24-slide** outline. Original slides were **not** inspected.

## API accuracy

Control-plane routes in Part E match `include_router` composition:

- Unauthenticated: `GET /`, `GET /health`, `GET /ready`.
- Bearer: targets, agents, cases, audit, correlation, reasoning.
- Detached Ed25519: `POST /api/v1/telemetry/ingest` only.
- **No** `GET /api/v1/telemetry/events`.

Error envelope documented as `{error:{code,message,details}}`.

## Question pack

- Exactly **100** numbered questions (`## Q1` … `## Q100`).
- Category counts: fundamentals 10, problem/objectives 8, architecture 12, frontend/backend 10, database/API 10, cybersecurity/telemetry 12, signatures/audit 8, neuro-symbolic 12, testing/research 8, limitations 10.
- Each item has QUESTION, SHORT ANSWER, DETAILED ANSWER, PROJECT-SPECIFIC IMPLEMENTATION, POSSIBLE FOLLOW-UP, BEST RESPONSE.

## Honesty checks

| Claim | Documentation stance |
| --- | --- |
| In-memory hotpatching | **NOT IMPLEMENTED** — stated on covers, fact sheet, Q&A |
| Host mitigation / isolation | **NOT IMPLEMENTED** |
| Laboratory envelopes as `/proc` | Forbidden; labelled `synthetic_lab` / LAB ENVELOPES |
| SAT = host safety | Forbidden; Z3 on recommendation Booleans |
| Risk score = probability | Forbidden; capped heuristic |
| CIC-IDS2017 results | Fail-closed / not present unless operator CSV |
| Phase 10 accuracy 1.0 | Synthetic n=12 only; cannot generalize |
| OIDC / WebSockets / telemetry list GET | **NOT IMPLEMENTED** |

## Secrets

Scanned markdown and extracted PDF text for private keys, `Bearer ey`, long base64 blobs. **None found.** Environment **variable names** (`DATABASE_URL`, `SYNAPSE_AUTH_TOKENS`) appear as configuration documentation, without values.

## Unverified / missing

- Original university PPT: **missing**.
- Whether a particular lab database still contains a seeded `live-lab-host` row: **UNVERIFIED** in this documentation pass (depends on runtime).
- Exact live risk number on a machine not running here: handbook example 43 is a **worked heuristic**, not a claim that the current DB equals 43.
- Docker Compose runtime in this agent VM: previously **unavailable**; host Postgres path is documented.

## Markdown vs PDF

HTML is generated from the same markdown. PDF text extraction contains titles, slide 1–24 headings, Q1 and Q100, ingest route, and hotpatching-not-implemented language. Print CSS uses A4, navy covers, tables, and stamped page numbers. Minor letter-spacing on the cover kicker may appear as spaced capitals in copy-paste; body text is normal.

## Git

Documentation files and the root ZIP are intended to be committed with message `docs: add complete Synapse-CRS presentation and viva package`. Do not commit `.env`, HTML print intermediates, `__pycache__`, or render helpers unless needed to rebuild PDFs.
