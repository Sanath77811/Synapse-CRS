# Telemetry redaction and normalization

This module prepares **raw observation dictionaries** supplied by a caller. It is not a collector. It does not read `/proc`, open sockets, or store data.

Three objects stay distinct:

1. **Raw observation input** — an untrusted dictionary. It may contain extra keys, paths, arguments, or addresses.
2. **Normalized telemetry envelope** — a Phase 1 `TelemetryEnvelope` with a closed field set.
3. **Cryptographically signed telemetry** — the same envelope plus a Phase 2 Ed25519 signature kept beside it, not inside it.

Redaction does not make hostile input safe in general. It only produces the constrained representation defined here.

## Purpose

Phase 1 rejects unknown fields. A future collector will see more keys than the contract allows. This layer copies only an allowlist, redacts values the contract cannot represent, then validates with the real Phase 1 model so the result can be signed with the real Phase 2 API.

## Allowlist

Unsupported keys are **discarded**. They are never copied into the envelope. Extra keys do not fail an otherwise valid observation. Missing required fields and malformed required values are **rejected**.

| Event type | Copied payload fields |
|---|---|
| `process_started` | `pid`, `ppid`, `uid`, `start_ticks`, `comm` |
| `process_exited` | `pid`, `start_ticks` |
| `network_connection_observed` | `protocol`, `local_port`, `remote_port`, `remote_address`, `uid`, `pid` |

Identity fields copied from the raw object: `event_type`, `target_id`, `agent_id`, `boot_id`, `sequence`. Optional: `event_id`, `observed_at`. The module sets `schema_version`, `basis`, and `content_class` itself.

The API never reads `argv`, `cmdline`, `command`, `environ`, `exe`, `cwd`, `password`, `token`, or similar keys into the envelope.

## Redaction

- `comm` that already matches the Phase 1 pattern is kept. Any other string, including paths, spaces, overlong names, and secret-looking text, becomes `[redacted]`. Names are not truncated.
- `remote_address` is always the token `[ip]`. A raw IPv4 or IPv6 string is accepted as input and replaced. The original address is not stored.
- Non-string `comm` or `remote_address` is rejected.
- Error messages name the field (`pid is invalid`). They do not include the raw value.

## Numeric validation and protocols

Integers use the Phase 1 ranges. Booleans and numeric strings are rejected. `protocol` must be exactly `tcp`, `tcp6`, `udp`, or `udp6`. Network `pid` may be `null`.

## Timestamps and UUIDs

`event_id` and `observed_at` may be supplied on the raw object. If they are omitted, the caller may inject `event_id_factory` and `clock`. Defaults are `uuid4` and the current UTC time in `YYYY-MM-DDTHH:MM:SS.ffffffZ`. Tests inject both so output is deterministic. There is no process-global clock.

## Immutability

The input mapping is only read. Normalization does not write to it.

## Integration

```text
raw observation
    → normalize_observation / type-specific helpers
    → TelemetryEnvelope.model_validate
    → sign_event / verify_event
```

Canonicalization is not duplicated. Signatures stay outside the envelope.

## Example

Raw (synthetic laboratory data):

```json
{
  "event_type": "network_connection_observed",
  "protocol": "tcp",
  "remote_address": "192.0.2.10",
  "cmdline": "curl https://192.0.2.10",
  "local_port": 40000,
  "remote_port": 443,
  "uid": 1000,
  "pid": 4242
}
```

Normalized payload:

```json
{
  "protocol": "tcp",
  "local_port": 40000,
  "remote_port": 443,
  "remote_address": "[ip]",
  "uid": 1000,
  "pid": 4242
}
```

`cmdline` is absent. `192.0.2.10` is absent.

## Tests

```bash
.venv/bin/pytest tests/unit/test_telemetry_normalization.py
.venv/bin/pytest
PYTHONPATH=packages/telemetry/src .venv/bin/python -m synapse_telemetry.demo
```

## Privacy limitations

A caller who already holds the raw dictionary still has the secrets. This module only prevents those values from entering the signed contract. It does not encrypt memory, wipe caller data, or authorize an agent.
