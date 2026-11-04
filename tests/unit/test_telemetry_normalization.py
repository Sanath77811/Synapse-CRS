"""Allowlist normalization produces Phase 1 envelopes and never copies extras."""

import json
from copy import deepcopy

import pytest
from synapse_telemetry.envelope import (
    EVENT_TYPES,
    PID_MAX,
    PORT_MAX,
    REDACTED_ADDRESS,
    REDACTED_COMM,
    UID_MAX,
    TelemetryEnvelope,
)
from synapse_telemetry.normalization import (
    NormalizationError,
    discarded_keys,
    normalize_network_connection,
    normalize_observation,
    normalize_process_exited,
    normalize_process_started,
)
from synapse_telemetry.signatures import (
    SignatureError,
    generate_signing_key,
    sign_event,
    verify_event,
)

FIXED_IDS = {
    "target_id": "22222222-2222-4222-8222-222222222222",
    "agent_id": "33333333-3333-4333-8333-333333333333",
    "boot_id": "44444444-4444-4444-8444-444444444444",
}
FIXED_EVENT = "11111111-1111-4111-8111-111111111111"
FIXED_TIME = "2026-09-29T17:34:00.000000Z"
DOCUMENTATION_IP = "192.0.2.10"


def _identity(overrides: dict[str, object] | None = None) -> dict[str, object]:
    body: dict[str, object] = {
        "target_id": FIXED_IDS["target_id"],
        "agent_id": FIXED_IDS["agent_id"],
        "boot_id": FIXED_IDS["boot_id"],
        "sequence": 1,
        "event_id": FIXED_EVENT,
        "observed_at": FIXED_TIME,
    }
    if overrides:
        body.update(overrides)
    return body


def _started(**extra: object) -> dict[str, object]:
    body = _identity(
        {
            "event_type": "process_started",
            "pid": 4242,
            "ppid": 1,
            "uid": 1000,
            "start_ticks": 123456,
            "comm": "python3",
        }
    )
    body.update(extra)
    return body


def _exited(**extra: object) -> dict[str, object]:
    body = _identity({"event_type": "process_exited", "pid": 4242, "start_ticks": 123456})
    body.update(extra)
    return body


def _network(**extra: object) -> dict[str, object]:
    body = _identity(
        {
            "event_type": "network_connection_observed",
            "protocol": "tcp",
            "local_port": 40000,
            "remote_port": 443,
            "remote_address": DOCUMENTATION_IP,
            "uid": 1000,
            "pid": 4242,
        }
    )
    body.update(extra)
    return body


def _dump(envelope: TelemetryEnvelope) -> str:
    return json.dumps(envelope.model_dump(mode="json"), sort_keys=True)


def test_valid_process_started_is_normalized_and_closed() -> None:
    envelope = normalize_process_started(_started())
    document = envelope.model_dump(mode="json")
    assert set(document) == {
        "schema_version",
        "event_id",
        "event_type",
        "target_id",
        "agent_id",
        "boot_id",
        "sequence",
        "observed_at",
        "basis",
        "content_class",
        "payload",
    }
    assert document["payload"] == {
        "pid": 4242,
        "ppid": 1,
        "uid": 1000,
        "start_ticks": 123456,
        "comm": "python3",
    }
    TelemetryEnvelope.model_validate(document)


def test_valid_process_exited_omits_exit_codes() -> None:
    envelope = normalize_process_exited(_exited(exit_code=9, command="/bin/sh"))
    document = envelope.model_dump(mode="json")
    assert document["payload"] == {"pid": 4242, "start_ticks": 123456}
    assert "exit_code" not in document["payload"]
    assert "/bin/sh" not in _dump(envelope)


@pytest.mark.parametrize("protocol", ["tcp", "tcp6", "udp", "udp6"])
def test_valid_network_protocols_redact_addresses(protocol: str) -> None:
    envelope = normalize_network_connection(
        _network(protocol=protocol, remote_address="2001:db8::1")
    )
    document = envelope.model_dump(mode="json")
    assert document["payload"]["protocol"] == protocol
    assert document["payload"]["remote_address"] == REDACTED_ADDRESS
    assert "2001:db8::1" not in _dump(envelope)
    assert DOCUMENTATION_IP not in _dump(envelope)


def test_injected_providers_are_deterministic() -> None:
    first = normalize_observation(
        _started(), event_id_factory=lambda: FIXED_EVENT, clock=lambda: FIXED_TIME
    )
    second = normalize_observation(
        _started(), event_id_factory=lambda: FIXED_EVENT, clock=lambda: FIXED_TIME
    )
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.model_dump(mode="json")["event_id"] == FIXED_EVENT
    assert first.model_dump(mode="json")["observed_at"] == FIXED_TIME


def test_normalized_output_signs_and_verifies() -> None:
    envelope = normalize_observation(_started())
    key = generate_signing_key()
    signature = sign_event(key, envelope)
    verify_event(key.public_key(), envelope, signature)
    tampered = envelope.model_dump(mode="json")
    tampered["payload"]["comm"] = "nginx"
    with pytest.raises(SignatureError):
        verify_event(key.public_key(), tampered, signature)
    identity = envelope.model_dump(mode="json")
    identity["target_id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    with pytest.raises(SignatureError):
        verify_event(key.public_key(), identity, signature)


def test_sensitive_fields_are_not_copied_or_echoed() -> None:
    raw = _started(
        argv=["/usr/bin/python3", "-c", "password=hunter2"],
        cmdline="/usr/bin/python3 -c token=abcd",
        environ={"SECRET": "supersecret", "API_TOKEN": "tok_live_example"},
        exe="/usr/bin/python3",
        cwd="/home/lab",
        password="hunter2",
        comm="/usr/bin/python3",
    )
    snapshot = deepcopy(raw)
    try:
        envelope = normalize_observation(raw)
    except NormalizationError as exc:
        text = str(exc)
        assert "hunter2" not in text
        assert "supersecret" not in text
        raise
    dumped = _dump(envelope)
    for token in (
        "/usr/bin/python3",
        "hunter2",
        "supersecret",
        "tok_live_example",
        "argv",
        "environ",
        "cmdline",
        "password",
        "/home/lab",
    ):
        assert token not in dumped
    assert envelope.payload.comm == REDACTED_COMM
    assert raw == snapshot
    assert set(discarded_keys(raw, "process_started")) == {
        "argv",
        "cmdline",
        "environ",
        "exe",
        "cwd",
        "password",
    }


def test_network_address_becomes_redaction_token() -> None:
    raw = _network(remote_address=DOCUMENTATION_IP, cmdline="curl https://192.0.2.10")
    envelope = normalize_observation(raw)
    assert envelope.payload.remote_address == REDACTED_ADDRESS
    dumped = _dump(envelope)
    assert DOCUMENTATION_IP not in dumped
    assert "curl" not in dumped


def test_input_dictionary_is_not_mutated() -> None:
    raw = _started(argv=["id"])
    snapshot = json.dumps(raw, sort_keys=True)
    normalize_observation(raw)
    assert json.dumps(raw, sort_keys=True) == snapshot
    assert raw["argv"] == ["id"]


def test_missing_required_fields_are_rejected() -> None:
    raw = _started()
    del raw["pid"]
    with pytest.raises(NormalizationError, match="pid is missing"):
        normalize_observation(raw)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("protocol", "icmp"),
        ("protocol", "TCP"),
        ("pid", 0),
        ("pid", PID_MAX + 1),
        ("uid", -1),
        ("uid", UID_MAX + 1),
        ("local_port", -1),
        ("local_port", PORT_MAX + 1),
        ("remote_port", 65536),
        ("pid", True),
        ("local_port", "443"),
        ("uid", "1000"),
        ("observed_at", "2026-09-29T17:34:00"),
        ("event_id", "not-a-uuid"),
        ("target_id", "11111111-1111-1111-8111-111111111111"),
        ("pid", {"nested": 1}),
        ("remote_address", None),
        ("remote_address", ""),
        ("remote_address", 1),
        ("protocol", None),
    ],
)
def test_invalid_network_values_are_rejected_without_echo(field: str, value: object) -> None:
    raw = _network()
    raw[field] = value
    with pytest.raises(NormalizationError) as caught:
        normalize_observation(raw)
    assert DOCUMENTATION_IP not in str(caught.value)
    assert "nested" not in str(caught.value)
    assert "2001:db8" not in str(caught.value)


def test_invalid_task_name_is_redacted_not_truncated() -> None:
    envelope = normalize_process_started(_started(comm="thisnameistoolong"))
    assert envelope.payload.comm == REDACTED_COMM
    envelope = normalize_process_started(_started(comm="has space"))
    assert envelope.payload.comm == REDACTED_COMM
    with pytest.raises(NormalizationError, match="comm is invalid"):
        normalize_process_started(_started(comm=123))


def test_unexpected_event_types_and_non_objects_are_rejected() -> None:
    with pytest.raises(NormalizationError, match="event type is unsupported"):
        normalize_observation(_started(event_type="command_executed"))
    with pytest.raises(NormalizationError, match="observation must be an object"):
        normalize_observation(["pid", 1])  # type: ignore[arg-type]
    with pytest.raises(NormalizationError, match="event type is unsupported"):
        normalize_process_started(_exited())


def test_large_dictionaries_and_non_string_keys_are_not_copied() -> None:
    raw: dict[object, object] = _started()
    for index in range(4000):
        raw[str(index)] = {"secret": "hunter2"}
    raw[1] = "ignored-non-string-key"
    envelope = normalize_observation(raw)
    dumped = _dump(envelope)
    assert "hunter2" not in dumped
    assert "ignored-non-string-key" not in dumped
    assert set(envelope.model_dump(mode="json")["payload"]) == {
        "pid",
        "ppid",
        "uid",
        "start_ticks",
        "comm",
    }


def test_all_event_types_are_supported() -> None:
    assert {
        normalize_observation(_started()).event_type,
        normalize_observation(_exited()).event_type,
        normalize_observation(_network()).event_type,
    } == set(EVENT_TYPES)


def test_null_network_pid_is_allowed() -> None:
    envelope = normalize_network_connection(_network(pid=None))
    assert envelope.payload.pid is None


def test_error_messages_do_not_contain_raw_observations() -> None:
    raw = _started(pid="4242", password="hunter2")
    with pytest.raises(NormalizationError, match="pid is invalid") as caught:
        normalize_observation(raw)
    assert "hunter2" not in str(caught.value)
    assert "4242" not in str(caught.value)
