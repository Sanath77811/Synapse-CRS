# Telemetry contract 1.0.0

Phase 1 defines the observation contract only. No agent is collecting events, no signature is checked, and no telemetry table exists.

## Version

The envelope field `schema_version` is required and is exactly `1.0.0`. There is no `latest` alias. A breaking change needs a new schema file and a new constant. This number is independent of the v0.1 control-plane `contract_version`: telemetry can change without pretending the case machine changed.

## Event types

Only these observation types are valid:

- `process_started`
- `process_exited`
- `network_connection_observed`

## Collection basis and content class

`basis` is `procfs_poll`. `content_class` is `observation`. Other bases and classes are rejected, including kernel or packet mechanisms that are not implemented.

## Field philosophy

Telemetry is untrusted data. Fields describe what a later procfs poll could honestly report. They are not commands. Schemas set `additionalProperties` to false, so a document cannot add `command`, `shell`, `argv`, `environ`, or any other key.

Identifiers `event_id`, `target_id`, `agent_id`, and `boot_id` are canonical lowercase UUID version 4 strings (36 characters). `target_id` matches the existing target primary key. `boot_id` uses that form because the kernel boot identifier is a random UUID. The pattern rejects spaces, newlines, and other control characters. This phase does not look the identifiers up.

`sequence` is an integer from 1 through 2^63-1. Replay rules are not part of this contract.

`observed_at` uses the audit-chain form `YYYY-MM-DDTHH:MM:SS.ffffffZ`. Naive times and numeric offsets are rejected. The JSON Schema pattern bounds that shape. The Python model also rejects impossible civil dates, such as February 31, which the pattern still allows.

`comm` is at most 15 characters: a safe task name, or the token `[redacted]`. It is not a command line. `remote_address` is only `[ip]`. A raw address cannot be represented until a later schema version says so.

## Intentionally not represented

Arguments, environment variables, file contents, paths, passwords, tokens, exit codes, signals, raw addresses, local addresses, names, packet bytes, headers, and cookies are not fields. Signing keys and signatures are not fields yet.

`process_exited` means a previously seen `pid` and `start_ticks` pair was absent on a later poll. It does not claim an exact kernel exit.

## Known limitation

Procfs polling is not implemented. Accepting a document only means the document matches this contract.
