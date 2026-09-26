# ADR 0005: Lab scope and a closed capability list

## Status

Accepted for v0.1.

## Context

The registry must not become an open permission to name arbitrary hosts or arbitrary future actions. v0.1 also must not connect to anything a caller writes down.

## Decision

`scope.environment` is `lab` or `development`. Assets are short identifiers. Unbounded values such as `*` are rejected. Capabilities are exactly:

- `telemetry.ingest`
- `evidence.submit`
- `reasoning.request`
- `verification.request`

No capability in this list is implemented. Names that would imply shell execution or mitigation are not accepted.

## Consequences

A production environment cannot be registered until a later version defines production controls. New capabilities are a schema change, not a free-text field.
