# ADR 0002: Bearer tokens for v0.1

## Status

Accepted for v0.1.

## Context

The foundation needs an authentication boundary before any real operator data exists. A full identity provider is a larger choice than this version needs.

## Decision

Operators present bearer tokens declared in `SYNAPSE_AUTH_TOKENS`. Roles are `admin` and `viewer`. Actors must be unique. The process will not start with an empty set. Production mode requires 32-character tokens and turns off interactive API docs.

A distinct approver role waits until a version can apply a host change.

## Consequences

Tokens are shared secrets. They are appropriate for a local research deployment and are the wrong control for an internet-facing multi-tenant service. Replacing them with OIDC can sit in front of the same role checks.
