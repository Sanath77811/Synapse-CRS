# Claims and limitations

## What v0.1 does

These statements match tests in this repository:

- The API starts only with a database URL and a non-empty token configuration.
- Unauthenticated registry calls are rejected.
- A viewer cannot create or revoke a target.
- A target can be stored with an owner, scope, expiry, capability allowlist, and timestamps.
- A target whose expiry is not in the future, or whose authorization is revoked, is not eligible. The API will not open or advance a case for it.
- Scope values outside `lab` and `development`, empty asset lists, unbounded asset names, and capabilities outside the allowlist are rejected.
- Case state moves only along the documented linear path. A skipped or backward move is rejected.
- A transition into `ACTION`, and every other transition, records `executed: false` and does not start a program.
- Audit events form a hash chain from a genesis hash. `/api/v1/audit/verify` replays that chain.
- The application role cannot update audit events. A table-owner `UPDATE`, `DELETE`, or `TRUNCATE` hits an append-only trigger.

## What v0.1 does not do

Do not describe the current system as any of the following. They are research goals for later versions, and only after implementation, tests, and published limits:

- Discovery of unknown vulnerabilities or zero-days
- Automatic or assisted exploitation
- Automatic binary patching or hotpatching
- Zero-downtime remediation
- A mathematical guarantee that a host, program, or configuration is secure
- Runtime enforcement with eBPF
- Model-based security reasoning
- Formal verification with Z3 or any other solver

The case state name `VERIFICATION` is a label in a state machine. Reaching it does not verify a property.

## Audit limitation

The hash chain and the append-only trigger are tamper-evidence and tamper-resistance for the application role. They are not absolute tamper-proof logging. A database owner can disable triggers. Verification of the chain detects a bad link only if the modified rows are still the rows the verifier reads.

## Authorization limitation

The registry does not prove that a target is owned or that a test is authorized. It records an operator's assertion and then refuses to proceed when that record is missing, revoked, or expired.

## Execution limitation

v0.1 has no command API, no shell integration, and no client that connects to a target. Capability names such as `telemetry.ingest` reserve vocabulary for later versions. They do not enable collection.
