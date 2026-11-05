# Synapse-CRS presentation and viva package

Use this folder to prepare a university presentation and technical viva on **the software that is actually in this repository**. It is an observer-only laboratory control plane and investigation console. In-memory hotpatching is **not implemented**.

## What to read first

1. **`IMPLEMENTATION_FACT_SHEET.md`** — short status table (IMPLEMENTED / PARTIAL / PLANNED / NOT IMPLEMENTED / UNVERIFIED). Read this before any slide or viva answer.
2. **`SYNAPSE_CRS_COMPLETE_USER_AND_TECHNICAL_GUIDE.pdf`** (or `.md`) — install, every console route, architecture, API table, security, operations.
3. **`SYNAPSE_CRS_PRESENTATION_MASTER_HANDBOOK.pdf`** — suggested speaking notes.
4. **`SYNAPSE_CRS_100_VIVA_QUESTIONS_AND_ANSWERS.pdf`** — drill.
5. **`DOCUMENTATION_VALIDATION_REPORT.md`** — what was inspected and what is missing.

## What each document contains

| File | Contents |
| --- | --- |
| `SYNAPSE_CRS_COMPLETE_USER_AND_TECHNICAL_GUIDE` | Parts A–H: getting started, every frontend route, architecture, codebase, API reference, security, troubleshooting, limitations, glossary |
| `SYNAPSE_CRS_PRESENTATION_MASTER_HANDBOOK` | Suggested 24-slide script, formulas, live demo walkthrough |
| `SYNAPSE_CRS_100_VIVA_QUESTIONS_AND_ANSWERS` | Exactly 100 questions with short, detailed, implementation-specific, and follow-up answers |
| `IMPLEMENTATION_FACT_SHEET.md` | Capability inventory grounded in source |
| `DOCUMENTATION_VALIDATION_REPORT.md` | Checks run on this pack |
| `README.md` | This index |

**There is no original `.ppt` / `.pptx` in the repository.** The handbook is a **suggested** outline. Do not tell examiners it was transcribed from an inspected slide deck unless you bring your own file.

## How to prepare the presentation

1. Memorize handbook **Slide 1–2** honesty: observer-only, no hotpatch, no host execution.
2. Walk slides 3–24 using the **What to say** paragraphs (~45–70 seconds each).
3. Rehearse the **Live demonstration script**: Command Centre → Telemetry → Evidence Lab → Threat Graph → Reasoning → Hypotheses → Defence → Control (audit) → Research observatory.
4. If the HUD shows **LAB ENVELOPES**, say the records are **constructed signed envelopes** ingested through `POST /api/v1/telemetry/ingest` with `dataset_label=synthetic_lab`. They are **not** `/proc` telemetry.
5. If the API is down, use **Demonstration mode** and say those rows are **browser fixtures**.

## How to use the 100 viva questions

- Categories: fundamentals (10), problem/objectives (8), architecture (12), frontend/backend (10), database/API (10), cybersecurity/telemetry (12), signatures/audit (8), neuro-symbolic (12), testing/research (8), limitations (10).
- Speak the **SHORT ANSWER** first (20–30 seconds). Use **DETAILED ANSWER** if asked to expand. Use **BEST RESPONSE** for the listed follow-up.
- If you do not remember an endpoint, say you will check OpenAPI `/docs`. Do **not** invent `GET /api/v1/telemetry/events` — that route does not exist.

## Important limitations (do not overclaim)

- No in-memory hotpatching, isolation, or other host mitigation.
- SAT/UNSAT from Z3 is a check of **encoded recommendation Booleans**, not host safety.
- Risk score is a **capped heuristic**, not a probability of compromise.
- Phase 10 metrics are **synthetic, n=12**. CIC-IDS2017 / DMBD evaluations **fail closed** unless the operator supplies the corpus.
- Bearer tokens are shared secrets (ADR 0002). There is no OIDC login.
- Append-only audit triggers apply to the application role; a database owner can still rewrite history.

## ZIP location

A downloadable archive of the three PDFs, three Markdown manuals, the fact sheet, and the validation report is at the **repository root**:

`SYNAPSE_CRS_COMPLETE_PRESENTATION_PACKAGE.zip`

This folder may also contain HTML print intermediates and Python render helpers; they are not required to study for the viva.
