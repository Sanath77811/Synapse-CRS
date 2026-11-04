# Phase 12 research results

Status: **EXPERIMENTAL**. Phase 10 and Phase 11 findings are preserved.

## Independent endpoint validation

**dmbd_evaluated=False**
**winmet_evaluated=False**
**optc_evaluated=False**
**independent_endpoint_validation_completed=False**

Blocker: No independent endpoint dataset is present. Set SYNAPSE_DMBD_JSONL to a local JSONL of DMBD-like process rows. This command does not download DMBD, WinMET, or OpTC, and does not fall back to fixtures.

No independent endpoint benchmark metrics were produced.

## Suitability matrix

[
  {
    "capability": "Process creation",
    "dmbd": "documented-unverified",
    "winmet": "documented-unverified",
    "optc": "documented-unverified"
  },
  {
    "capability": "Process termination",
    "dmbd": "documented-unverified",
    "winmet": "documented-unverified",
    "optc": "documented-unverified"
  },
  {
    "capability": "Parent-child tree",
    "dmbd": "documented-unverified",
    "winmet": "documented-unverified",
    "optc": "documented-unverified"
  },
  {
    "capability": "Stable process identity",
    "dmbd": "documented-unverified",
    "winmet": "documented-unverified",
    "optc": "documented-unverified"
  },
  {
    "capability": "PID reuse validation",
    "dmbd": "supported if pid_hash differs for reused os_pid; files absent",
    "winmet": "unverified locally",
    "optc": "unverified locally"
  },
  {
    "capability": "Process-network association",
    "dmbd": "documented-unverified",
    "winmet": "documented-unverified",
    "optc": "documented-unverified"
  },
  {
    "capability": "Event-level labels",
    "dmbd": "not a sample-level AV consensus; event labels unavailable",
    "winmet": "family labels are trace-level, not per API call",
    "optc": "contested / external labeling; files absent"
  },
  {
    "capability": "Sample-level labels",
    "dmbd": "documented (benign/malicious); files absent",
    "winmet": "documented-unverified",
    "optc": "documented-unverified"
  },
  {
    "capability": "Independent ground truth",
    "dmbd": "documented-unverified",
    "winmet": "documented-unverified",
    "optc": "documented-unverified"
  },
  {
    "capability": "Enterprise endpoint realism",
    "dmbd": "Windows (Wintap); not Linux procfs telemetry; files absent",
    "winmet": "Windows sandbox, not continuous enterprise telemetry; files absent",
    "optc": "Windows 10 enterprise testbed (500 hosts in the released data); files absent"
  }
]

## Preserved prior findings

{
  "available": true,
  "name": "phase10",
  "experiment_id": "phase10-research-validation-v1",
  "must_not_rewrite": true
}

{
  "available": true,
  "name": "phase11",
  "experiment_id": "phase11-flow-benchmark-v1",
  "must_not_rewrite": true
}

## Limitations

- Do not treat sample AV labels as event-level malice.
- Do not map pid_hash onto Linux boot_id/start_ticks.
- SAT/Z3 remains a policy-model result, not real-world safety.

