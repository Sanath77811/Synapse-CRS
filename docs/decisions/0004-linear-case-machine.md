# ADR 0004: Linear case transitions

## Status

Accepted for v0.1.

## Context

The pipeline was specified as one sequence from `AUTHORIZED_TARGET` through `SEALED_AUDIT`. Early rollback and cancellation were not specified.

## Decision

Only the single forward edge from each state is legal. `SEALED_AUDIT` has no successor. The API checks target eligibility before every move. The move is a database update and an audit event. The payload records `executed: false`.

## Consequences

A case cannot jump to `ROLLBACK` from `ACTION` or be abandoned in v0.1. If a later version needs those edges, they require a new decision and new tests. Until then, an expired authorization freezes the case where it is.
