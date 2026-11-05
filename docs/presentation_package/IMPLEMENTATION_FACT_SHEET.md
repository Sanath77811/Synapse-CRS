# Synapse-CRS implementation fact sheet

Inspected from repository source (not the product name or `docs/roadmap.md`).  
Roadmap file still says later stages are unimplemented; **that file is stale**. Telemetry, correlation, hybrid reasoning, Z3 policy checks, Linux agent, research harnesses, and the React console **are present in the tree**. Hotpatching and host mitigation **are not**.

Status vocabulary: **IMPLEMENTED** | **PARTIAL** | **PLANNED** | **NOT IMPLEMENTED** | **UNVERIFIED**.

## Product identity

| Claim | Status |
| --- | --- |
| Observer-only control plane (FastAPI + PostgreSQL) | IMPLEMENTED |
| React investigation console | IMPLEMENTED |
| Bearer admin/viewer tokens (`SYNAPSE_AUTH_TOKENS`) | IMPLEMENTED |
| Target registry, eligibility, one-way revocation | IMPLEMENTED |
| Linear case state machine; `executed` always false | IMPLEMENTED |
| SHA-256 audit hash chain + `/audit/verify` | IMPLEMENTED |
| Append-only triggers for `audit_events` / `telemetry_events` | IMPLEMENTED (app role); DB owner can disable triggers |
| Ed25519 signed telemetry envelopes | IMPLEMENTED |
| Agent enrollment + HTTP ingest | IMPLEMENTED |
| Linux procfs collector | IMPLEMENTED (lab agent; not a fleet product) |
| GET list of raw telemetry events | **NOT IMPLEMENTED** (ingest POST only) |
| Deterministic correlation + findings + risk heuristic | IMPLEMENTED |
| Hybrid reconstruction, Isolation Forest baseline, symbolic rules | IMPLEMENTED |
| Z3 check of **recommendation records** | IMPLEMENTED |
| Automatic host mitigation / isolation | **NOT IMPLEMENTED** |
| In-memory hotpatching / binary patching | **NOT IMPLEMENTED** |
| eBPF runtime enforcement | **NOT IMPLEMENTED** |
| Zero-day discovery | **NOT IMPLEMENTED** |
| OIDC / username-password login | **NOT IMPLEMENTED** |
| WebSockets | **NOT IMPLEMENTED** |
| Independent CIC-IDS2017 evaluation | **NOT IMPLEMENTED** (fail-closed unless CSV supplied) |
| Independent DMBD/WinMET/OpTC process-tree evaluation | **NOT IMPLEMENTED** (fail-closed) |
| Phase 10 synthetic comparison (12 reconstructions) | IMPLEMENTED (synthetic only; not enterprise rates) |

## Versions in code

- API version: `0.1.0` (`synapse_contracts.version.API_VERSION`)
- Contract version: `1.0.0`
- Reasoning engine version: `0.6.0` (hybrid package)
- Frontend package: `0.1.0`

## Frontend routes (actual `App.tsx`)

`/session`, `/`, `/telemetry`, `/evidence`, `/investigations`, `/investigations/:caseId`, `/graph`, `/reasoning`, `/hypotheses`, `/defence`, `/research`, `/research/:phaseId`, `/control`. Unknown paths redirect to `/`.

## HTTP surface (actual routers)

See user guide Part E. Control-plane `/api/v1/*` uses bearer tokens except telemetry ingest (detached Ed25519 vs enrolled public key). `/health` and `/ready` are unauthenticated. `GET /` returns a service summary.

## Error envelope

`{"error":{"code":"...","message":"...","details":{}}}` (`synapse_api.errors.error_body`).

## Laboratory demonstration data

If `dataset_label=synthetic_lab`, the console shows **LAB ENVELOPES**: constructed signed envelopes ingested through the real `POST /api/v1/telemetry/ingest`. **Not `/proc` telemetry.** Browser **DEMO MODE** uses `frontend/src/data/demo.ts` fixtures and is labelled separately. Live API failures must not swap in demo rows.

## Formulas implemented

1. Audit: `SHA-256(canonical JSON of event including previous_event_hash)`; genesis `0*64`.
2. Risk: `min(100, Σ capped groups)` in `packages/correlation/.../scoring.py`.
3. Hybrid hypothesis selection: max support; ties prefer `H4_insufficient_evidence` then `H1_normal`.
4. Z3 policy: `¬executed ∧ ¬destructive ∧ authorized ∧ in_scope ∧ identity_certain ∧ evidence_present ∧ (impactful → human_approved) ∧ ¬mitigation_kind`.

## Presentation files

**No `.ppt`, `.pptx`, or project presentation `.pdf` exists in this repository.** Document 2 uses a **suggested** 24-slide outline. Do not claim original slides were inspected.

## Inspection inventory (this pack)

| Area | Paths |
| --- | --- |
| HTTP | `apps/api/src/synapse_api/routers/`, `main.py` |
| Persistence | `apps/api` models + Alembic `0001`–`0006` |
| Console | `frontend/src/App.tsx`, `pages/`, `hooks/usePlatform.ts` |
| Correlation / risk | `packages/correlation/.../scoring.py` |
| Hybrid / Z3 | `packages/reasoning/.../hybrid.py`, `verification.py` |
| Signatures / audit | `packages/telemetry/signatures.py`, `packages/audit/chain.py` |
| Research | `docs/research/benchmark-results.md`, `packages/validation` |
| Claims | `docs/safety/claims.md` |

Status of this fact sheet: grounded in those files. Runtime database contents of any one demo host are **UNVERIFIED** until `/ready` and snapshot GETs are executed.
