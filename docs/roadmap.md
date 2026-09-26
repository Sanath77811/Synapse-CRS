# Roadmap

Stages after v0.1 are research milestones. A stage that misses its acceptance bar stops there. None of these stages is implemented in the current tree.

## v0.1 — Foundation

In progress in this repository. Acceptance criteria are in [development/v0.1-acceptance.md](development/v0.1-acceptance.md).

## v0.2 — Telemetry

A Python lab agent enrolls only to a pre-authorized target and submits a small allowlisted event schema. The agent refuses to start when authorization is missing or expired. Stored events pass the redaction tests. An unknown schema major version is rejected. A single lab host sustains a recorded rate for a fixed window, with an explicit drop count.

## v0.3 — Vulnerability evidence

An evidence package for an owned fixture receives a reproducibility verdict inside a runner with no outbound network and CPU, memory, and time limits. A benign fixture can be marked reproduced. An egress attempt does not complete a connection. An unauthorized target never starts a runner.

## v0.4 — Reasoning

A provider interface returns a structured hypothesis. A mock provider is what CI trusts. Hypotheses that cite missing evidence or name an action outside a catalog are rejected and audited. The pipeline still does not change a host.

## v0.5 — Formal verification

Z3 checks an explicit, narrow property list generated from the same policy object the runtime uses: consistency, capability subset, parameter bounds, a declared inverse, and a lease bound. Solver timeout rejects the proposal. The specification states which questions are outside those properties. This stage does not prove a host is secure.

## v0.6 — Controlled mitigation

A catalog of two or three reversible lab actions requires a human approval bound to the proposal hash. Unapproved proposals leave the host unchanged. Each inverse is tested. The approver is a distinct role from a read-only analyst.

## v0.7 — Continuous validation

A failed post-condition or an expired lease reverts the catalog action without a model call. A second revert is a no-op. A failed revert freezes the target. Rollback is audited.

## v0.8 — Integrated prototype

One laboratory scenario runs from a fixture through audit, with a human approval in the trace, using the mock provider in CI. The claims document lists only the behavior that scenario exercises.

eBPF remains optional and only as a pre-reviewed program if userspace collection cannot meet the v0.2 measurement. Hotpatching of arbitrary binaries is not on this roadmap.
