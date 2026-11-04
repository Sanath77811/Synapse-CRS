# Phase 13 methodology

Status: **IMPLEMENTED** as acquisition bounds, DMBD label inspection, completeness-aware sample reasoning, and fail-closed evaluation. Independent DMBD/WinMET/OpTC **process** evaluation: **NOT COMPLETED** unless `SYNAPSE_DMBD_JSONL` points at real process rows and the runner reports `scientific_completion=True`.

Phase 10–12 generated files are preserved.

## Research questions

RQ1–RQ8 from the Phase 13 charter. Reconstruction **accuracy** is reported only with independent edge ground truth. Otherwise only structural consistency is reported.

## Identity

Prefer observed `pid_hash` / `parent_pid_hash`. PID alone is never a global identity. Derived `os_pid+start` keys are labelled `derived_fallback`. Linux `boot_id` / `start_ticks` are never fabricated.

## Completeness-aware method

`completeness_aware_union_v1` uses train-only thresholds. If completeness is low and symbolic rules do not fire, the decision is `insufficient` (counted as not malicious for detection metrics, with `abstain_count` recorded). This is **not** Phase 9 hybrid and **not** a calibrated probability.

## Commands

Fail closed (exit 2 when process evidence is missing):

```bash
make research-eval-phase13
```

Explicit synthetic protocol (never labelled DMBD):

```bash
python -m synapse_validation.phase13 --synthetic-protocol tests/fixtures/validation/synthetic_endpoint_protocol.jsonl
```

Optional: `SYNAPSE_DMBD_LABELS_DIR` for official label JSON. `SYNAPSE_DMBD_JSONL` for process JSONL.
