# Telemetry signatures

Phase 2 signs a Phase 1 telemetry envelope with Ed25519. It does not enroll agents, accept events over HTTP, or decide authorization.

A valid signature proves that the holder of the matching private key signed that exact envelope. It does not prove the agent is authorized for the target. That binding is a later enrollment step: an administrator will register the public key for one agent and one eligible target. Phase 2 has no registry and no database write.

## Why Ed25519

Ed25519 is a fixed 64-byte signature over a 32-byte public key, implemented by the `cryptography` library. The project does not use RSA, ECDSA, HMAC, JWT, or a private curve implementation for this purpose.

## What is signed

The signed message is:

1. The ASCII domain `synapse-crs/telemetry-signature/1` and a newline.
2. The canonical UTF-8 JSON of the whole envelope.

The domain is fixed. It stops this signature from being treated as a signature for some other protocol that happens to use Ed25519. Changing the canonicalization rules later requires a new domain string.

The JSON object contains every Phase 1 field: `schema_version`, `event_id`, `target_id`, `agent_id`, `boot_id`, `event_type`, `sequence`, `observed_at`, `basis`, `content_class`, and `payload`. The signature is not an envelope field. A private key is never an envelope field.

`observed_at` stays `YYYY-MM-DDTHH:MM:SS.ffffffZ`.

## Canonical JSON

Canonical bytes use the same choices as the audit chain:

- UTF-8
- object keys sorted at every level
- separators `,` and `:` with no extra space
- `ensure_ascii` false

Integers stay integers. `true` is not `1`. `null` is preserved. Floats are not accepted. List order is preserved. Dict insertion order is not.

Phase 1 validation still runs before signing. An event the contract rejects is not signed.

## Signature encoding

An Ed25519 signature is 64 raw bytes. On the wire it is standard Base64 (alphabet `A-Za-z0-9+/`) with `==` padding, 88 characters, and no whitespace. URL-safe Base64, missing padding, truncated text, and raw bytes are rejected.

A public key inside this library is 32 raw bytes. Phase 2 does not store it.

## Keys

`generate_signing_key()` creates a private key in memory. The object has no export method. Its text form is `SigningKey(redacted)`. The agent side is the only place a private key should exist.

`public_key()` returns the matching public key. `verify_event()` checks a signature with that public key. Invalid signatures raise `SignatureError`. They are not returned as success.

## Not provided

No enrollment, key persistence, ingestion API, transport, collector, queue, or authorization decision. Possession of a private key is not permission to submit telemetry for a target.
