# Phase 12 methodology

Status: **IMPLEMENTED** as dataset discovery, a DMBD-oriented adapter, and structural reconstruction. Independent DMBD/WinMET/OpTC evaluation: **NOT COMPLETED** in this checkout (files absent).

Phase 10 and Phase 11 generated results are preserved and not reinterpreted.

## Research questions

RQ1 reconstruction; RQ2 suspicious behavior on independently labelled process evidence; RQ3 hybrid value with equivalent inputs; RQ4 explanations; RQ5 missing events / PID reuse / noise; RQ6 what cannot be validated.

## Primary adapter

**DMBD (LLNL Wintap)** is the preferred adapter target because public documentation describes `pid_hash`, parent hashes, lifecycle timestamps, sample-level AV labels, and an official train/test split. That preference is **not** an evaluation result. No DMBD files were downloaded.

Windows `pid_hash` is **not** mapped onto Linux `(agent_id, boot_id, pid, start_ticks)`. Phase 9 hybrid is **not comparable**.

Sample labels stay at **sample** scope.

## Commands

Fail closed:

```bash
make research-eval-phase12
```

Explicit synthetic protocol (never labelled DMBD):

```bash
python -m synapse_validation.phase12 --synthetic-protocol tests/fixtures/validation/synthetic_endpoint_protocol.jsonl
```
