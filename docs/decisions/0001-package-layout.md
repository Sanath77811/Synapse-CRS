# ADR 0001: Package layout

## Status

Accepted for v0.1.

## Context

The requested tree grouped contracts, policy, and audit as packages, with the API under `apps/api`. Case transitions are a separate set of rules. They must be tested without HTTP.

## Decision

Add `packages/cases` for the legal transition map. `apps/api` is the composition root: routing, SQLAlchemy, and transactions. JSON Schemas live in `schemas/` and are versioned `1.0.0`.

## Consequences

Import paths are explicit (`synapse_contracts`, `synapse_policy`, `synapse_cases`, `synapse_audit`, `synapse_api`). A future split into services can move a package without rewriting the state machine.
