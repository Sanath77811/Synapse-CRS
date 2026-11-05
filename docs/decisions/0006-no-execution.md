# ADR 0006: No execution in v0.1

## Status

Accepted for v0.1.

## Context

The state model includes `ACTION`, `VALIDATION`, and `ROLLBACK` because later versions need those names. Implementing them now would skip the evidence, reasoning, and verification stages.

## Decision

v0.1 does not ship an agent, a shell, a mitigation catalog, or a network client for targets. Transition requests are data. Tests walk a case to `SEALED_AUDIT` and assert `executed` is false. A source check rejects obvious command-execution imports in the foundation tree.

## Consequences

Demonstrations of v0.1 can show authorization and audit only. Any claim about defense, patching, or proof belongs to a later version that has its own tests.
