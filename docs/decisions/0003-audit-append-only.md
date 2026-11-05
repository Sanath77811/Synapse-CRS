# ADR 0003: Append-only audit with a hash chain

## Status

Accepted for v0.1.

## Context

Audit history has to survive ordinary application bugs and a curious operator using the application role. Absolute tamper-proof storage needs an anchor outside the database, which v0.1 does not operate.

## Decision

`audit_events` accepts inserts. Triggers reject `UPDATE`, `DELETE`, and `TRUNCATE`, including for the table owner, until that owner disables the trigger. The `synapse_app` role is not granted update or delete. Each event stores the previous event hash and its own SHA-256 hash. `sequence` orders the chain. `audit_chain_state` is mutable bookkeeping and is not itself the log. `/api/v1/audit/verify` replays the events and fails when the stored head hash or next sequence does not match that replay.

## Consequences

A migration user can still rewrite history by disabling triggers or replacing files. Documentation and the claims page say this directly. An external head-hash anchor is future work, not a v0.1 claim.
