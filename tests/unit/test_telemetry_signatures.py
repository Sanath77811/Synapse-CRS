"""Ed25519 telemetry signatures cover the Phase 1 envelope and reject tampering."""

import base64
import json
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import ValidationError
from synapse_telemetry.canonical import canonical_event_bytes, canonical_json_bytes
from synapse_telemetry.envelope import TelemetryEnvelope
from synapse_telemetry.signatures import (
    SIGNATURE_DOMAIN,
    SIGNATURE_LENGTH,
    SignatureError,
    VerificationKey,
    decode_signature,
    generate_signing_key,
    sign_event,
    signing_message,
    verify_event,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "telemetry"
PACKAGE = (
    Path(__file__).resolve().parents[2] / "packages" / "telemetry" / "src" / "synapse_telemetry"
)
OTHER_TARGET = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_AGENT = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
OTHER_EVENT = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
OTHER_BOOT = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
STARTED_CANONICAL = (
    '{"agent_id":"33333333-3333-4333-8333-333333333333",'
    '"basis":"procfs_poll",'
    '"boot_id":"44444444-4444-4444-8444-444444444444",'
    '"content_class":"observation",'
    '"event_id":"11111111-1111-4111-8111-111111111111",'
    '"event_type":"process_started",'
    '"observed_at":"2026-09-29T17:34:00.000000Z",'
    '"payload":{"comm":"python3","pid":4242,"ppid":1,"start_ticks":123456,"uid":1000},'
    '"schema_version":"1.0.0","sequence":1,'
    '"target_id":"22222222-2222-4222-8222-222222222222"}'
)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _started() -> dict:
    return _load("valid-process-started.json")


def _envelope(document: dict | None = None) -> TelemetryEnvelope:
    return TelemetryEnvelope.model_validate(_started() if document is None else document)


def _signed(document: dict | None = None):
    event = _started() if document is None else document
    key = generate_signing_key()
    signature = sign_event(key, event)
    return key, event, signature


def test_keypair_generation_is_fresh_and_matches() -> None:
    first = generate_signing_key()
    second = generate_signing_key()
    assert first.public_key().raw_bytes() != second.public_key().raw_bytes()
    assert len(first.public_key().raw_bytes()) == 32
    event = _started()
    signature = sign_event(first, event)
    verify_event(first.public_key(), event, signature)
    restored = VerificationKey.from_raw_bytes(first.public_key().raw_bytes())
    verify_event(restored, event, signature)
    with pytest.raises(SignatureError):
        verify_event(second.public_key(), event, signature)


def test_valid_signature_round_trip() -> None:
    key, event, signature = _signed()
    verify_event(key.public_key(), event, signature)
    verify_event(key.public_key(), _envelope(event), signature)
    assert sign_event(key, event) == signature
    assert len(decode_signature(signature)) == SIGNATURE_LENGTH
    assert len(signature) == 88


def test_canonical_bytes_are_independent_of_insertion_order() -> None:
    forward = _started()
    backward = {key: forward[key] for key in reversed(forward)}
    backward["payload"] = {key: forward["payload"][key] for key in reversed(forward["payload"])}
    assert canonical_event_bytes(_envelope(forward)) == canonical_event_bytes(_envelope(backward))
    assert canonical_event_bytes(_envelope(forward)) == STARTED_CANONICAL.encode("utf-8")
    key = generate_signing_key()
    assert sign_event(key, forward) == sign_event(key, backward)


def test_signing_message_uses_the_domain_and_every_field() -> None:
    message = signing_message(_envelope())
    assert message.startswith(SIGNATURE_DOMAIN)
    body = message.removeprefix(SIGNATURE_DOMAIN)
    assert body == STARTED_CANONICAL.encode("utf-8")
    text = body.decode("utf-8")
    for field in (
        "schema_version",
        "event_id",
        "target_id",
        "agent_id",
        "boot_id",
        "event_type",
        "sequence",
        "observed_at",
        "basis",
        "content_class",
        "payload",
    ):
        assert f'"{field}":' in text
    assert '"signature":' not in text


def test_domain_prefix_is_part_of_the_signed_message() -> None:
    key, event, signature = _signed()
    envelope = _envelope(event)
    raw = decode_signature(signature)
    public = Ed25519PublicKey.from_public_bytes(key.public_key().raw_bytes())
    public.verify(raw, signing_message(envelope))
    with pytest.raises(InvalidSignature):
        public.verify(raw, canonical_event_bytes(envelope))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_id", OTHER_TARGET),
        ("agent_id", OTHER_AGENT),
        ("event_id", OTHER_EVENT),
        ("boot_id", OTHER_BOOT),
        ("sequence", 2),
        ("observed_at", "2026-09-29T17:34:01.000000Z"),
    ],
)
def test_changing_a_signed_field_invalidates_the_signature(field: str, value: object) -> None:
    key, event, signature = _signed()
    tampered = json.loads(json.dumps(event))
    tampered[field] = value
    with pytest.raises(SignatureError, match="telemetry signature is invalid"):
        verify_event(key.public_key(), tampered, signature)


def test_payload_tampering_invalidates_the_signature() -> None:
    key, event, signature = _signed()
    tampered = json.loads(json.dumps(event))
    tampered["payload"]["comm"] = "nginx"
    with pytest.raises(SignatureError, match="telemetry signature is invalid"):
        verify_event(key.public_key(), tampered, signature)
    tampered = json.loads(json.dumps(event))
    tampered["payload"]["pid"] = 4243
    with pytest.raises(SignatureError, match="telemetry signature is invalid"):
        verify_event(key.public_key(), tampered, signature)


def test_event_type_tampering_invalidates_the_signature() -> None:
    key, event, signature = _signed()
    tampered = json.loads(json.dumps(event))
    tampered["event_type"] = "process_exited"
    tampered["payload"] = {"pid": 4242, "start_ticks": 123456}
    with pytest.raises(SignatureError, match="telemetry signature is invalid"):
        verify_event(key.public_key(), tampered, signature)


def test_basis_and_content_class_are_bound_by_the_signature() -> None:
    key, event, signature = _signed()
    raw = decode_signature(signature)
    public = Ed25519PublicKey.from_public_bytes(key.public_key().raw_bytes())
    message = bytearray(signing_message(_envelope(event)))
    basis_at = message.find(b"procfs_poll")
    message[basis_at + len(b"procfs_poll") - 1] = ord("x")
    with pytest.raises(InvalidSignature):
        public.verify(raw, bytes(message))
    message = bytearray(signing_message(_envelope(event)))
    class_at = message.find(b"observation")
    message[class_at + len(b"observation") - 1] = ord("x")
    with pytest.raises(InvalidSignature):
        public.verify(raw, bytes(message))
    for field, value in (("basis", "ebpf"), ("content_class", "command")):
        tampered = json.loads(json.dumps(event))
        tampered[field] = value
        with pytest.raises(ValidationError):
            verify_event(key.public_key(), tampered, signature)


def test_signature_cannot_be_reused_for_another_event() -> None:
    key, event, signature = _signed()
    other = json.loads(json.dumps(event))
    other["event_id"] = OTHER_EVENT
    other_signature = sign_event(key, other)
    with pytest.raises(SignatureError):
        verify_event(key.public_key(), other, signature)
    with pytest.raises(SignatureError):
        verify_event(key.public_key(), event, other_signature)


def test_wrong_public_key_is_rejected() -> None:
    key, event, signature = _signed()
    with pytest.raises(SignatureError, match="telemetry signature is invalid"):
        verify_event(generate_signing_key().public_key(), event, signature)


def test_random_truncated_and_modified_signatures_are_rejected() -> None:
    key, event, signature = _signed()
    public = key.public_key()
    random_signature = base64.standard_b64encode(b"\x11" * SIGNATURE_LENGTH).decode("ascii")
    with pytest.raises(SignatureError, match="telemetry signature is invalid"):
        verify_event(public, event, random_signature)
    with pytest.raises(SignatureError, match="telemetry signature encoding is invalid"):
        verify_event(public, event, signature[:-2])
    with pytest.raises(SignatureError, match="telemetry signature encoding is invalid"):
        verify_event(public, event, signature[:40])
    flipped = bytearray(decode_signature(signature))
    flipped[0] ^= 0x01
    with pytest.raises(SignatureError, match="telemetry signature is invalid"):
        verify_event(public, event, base64.standard_b64encode(bytes(flipped)).decode("ascii"))


def test_signature_encoding_is_standard_base64_only() -> None:
    _key, _event, signature = _signed()
    assert len(decode_signature(signature)) == SIGNATURE_LENGTH
    url_safe = signature.replace("+", "-").replace("/", "_")
    if url_safe != signature:
        with pytest.raises(SignatureError, match="telemetry signature encoding is invalid"):
            decode_signature(url_safe)
    with pytest.raises(SignatureError, match="telemetry signature encoding is invalid"):
        decode_signature("-" * 86 + "==")
    with pytest.raises(SignatureError, match="telemetry signature encoding is invalid"):
        decode_signature(signature[:-2])
    with pytest.raises(SignatureError, match="telemetry signature encoding is invalid"):
        decode_signature(b"\x00" * SIGNATURE_LENGTH)  # type: ignore[arg-type]
    with pytest.raises(SignatureError, match="telemetry signature encoding is invalid"):
        decode_signature(signature + "\n")


def test_nested_payload_key_order_does_not_change_canonical_bytes() -> None:
    started = _started()
    reordered = json.loads(json.dumps(started))
    reordered["payload"] = {
        "uid": started["payload"]["uid"],
        "comm": started["payload"]["comm"],
        "start_ticks": started["payload"]["start_ticks"],
        "ppid": started["payload"]["ppid"],
        "pid": started["payload"]["pid"],
    }
    assert canonical_event_bytes(_envelope(started)) == canonical_event_bytes(_envelope(reordered))
    nested = {"z": {"b": 1, "a": [True, None, 2]}, "a": 0}
    swapped = {"a": 0, "z": {"a": [True, None, 2], "b": 1}}
    assert canonical_json_bytes(nested) == canonical_json_bytes(swapped)
    assert canonical_json_bytes([1, True]) != canonical_json_bytes([True, 1])


def test_unicode_encoding_and_phase1_limits() -> None:
    encoded = canonical_json_bytes({"name": "é"})
    assert encoded == '{"name":"é"}'.encode()
    assert "é".encode() in encoded
    assert b"\\u00e9" not in encoded
    document = _started()
    document["payload"]["comm"] = "pythön"
    with pytest.raises(ValidationError):
        sign_event(generate_signing_key(), document)


def test_booleans_are_not_integers() -> None:
    assert canonical_json_bytes(True) == b"true"
    assert canonical_json_bytes(1) == b"1"
    assert canonical_json_bytes(False) == b"false"
    assert canonical_json_bytes(0) == b"0"
    assert canonical_json_bytes(None) == b"null"
    document = _started()
    document["sequence"] = True
    with pytest.raises(ValidationError):
        sign_event(generate_signing_key(), document)
    document = _started()
    document["payload"]["pid"] = True
    with pytest.raises(ValidationError):
        sign_event(generate_signing_key(), document)


def test_invalid_events_are_not_signed() -> None:
    key = generate_signing_key()
    missing = _started()
    del missing["target_id"]
    with pytest.raises(ValidationError):
        sign_event(key, missing)
    extra = _started()
    extra["command"] = "id"
    with pytest.raises(ValidationError):
        sign_event(key, extra)
    nested = _started()
    nested["payload"]["argv"] = ["id"]
    with pytest.raises(ValidationError):
        sign_event(key, nested)
    with pytest.raises(TypeError):
        sign_event(key, "not-an-event")


def test_null_network_pid_is_signed_and_bound() -> None:
    document = _load("valid-network-connection-observed.json")
    document["payload"]["pid"] = None
    key = generate_signing_key()
    signature = sign_event(key, document)
    verify_event(key.public_key(), document, signature)
    assert b'"pid":null' in canonical_event_bytes(_envelope(document))
    tampered = json.loads(json.dumps(document))
    tampered["payload"]["pid"] = 4242
    with pytest.raises(SignatureError):
        verify_event(key.public_key(), tampered, signature)


def test_private_keys_are_not_exported_or_embedded() -> None:
    key, event, signature = _signed()
    assert repr(key) == "SigningKey(redacted)"
    assert str(key) == "SigningKey(redacted)"
    assert repr(key.public_key()) == "VerificationKey(redacted)"
    assert key.public_key().raw_bytes().hex() not in repr(key)
    assert "signature" not in event
    source = (PACKAGE / "signatures.py").read_text(encoding="utf-8")
    assert "private_bytes" not in source
    try:
        verify_event(key.public_key(), event, "A" * 86 + "==")
    except SignatureError as exc:
        assert str(exc) == "telemetry signature is invalid"
        assert event["event_id"] not in str(exc)
        assert "A" * 20 not in str(exc)
    else:
        raise AssertionError("invalid signature was treated as valid")


def test_wrong_key_types_fail_cleanly() -> None:
    key, event, signature = _signed()
    with pytest.raises(TypeError):
        sign_event(key.public_key(), event)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        verify_event(key, event, signature)  # type: ignore[arg-type]
    with pytest.raises(SignatureError, match="telemetry verification key is invalid"):
        VerificationKey.from_raw_bytes(b"\x01" * 31)
    with pytest.raises(ValueError):
        canonical_json_bytes(1.0)
    with pytest.raises(ValueError):
        canonical_json_bytes({1: "a"})


def test_sign_event_does_not_mutate_the_document() -> None:
    document = _started()
    before = json.dumps(document, sort_keys=True)
    sign_event(generate_signing_key(), document)
    assert json.dumps(document, sort_keys=True) == before
