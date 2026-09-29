"""Telemetry contract 1.0.0: the model and JSON Schemas accept the same documents."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as SchemaValidationError
from pydantic import ValidationError
from referencing import Registry, Resource
from synapse_audit.chain import format_timestamp
from synapse_telemetry import (
    BASIS,
    COMM_MAX_LENGTH,
    COMM_PATTERN,
    CONTENT_CLASS,
    EVENT_TYPES,
    PID_MAX,
    PORT_MAX,
    REDACTED_ADDRESS,
    REDACTED_COMM,
    SCHEMA_VERSION,
    SEQUENCE_MAX,
    START_TICKS_MAX,
    TIMESTAMP_PATTERN,
    UID_MAX,
    UUID_V4_PATTERN,
    TelemetryEnvelope,
    format_observed_at,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
FIXTURES = ROOT / "tests" / "fixtures" / "telemetry"
PACKAGE = ROOT / "packages" / "telemetry" / "src" / "synapse_telemetry"
ENVELOPE_NAME = "telemetry-envelope-1.0.0.schema.json"
PAYLOAD_SCHEMAS = {
    "process_started": "telemetry-process-started-1.0.0.schema.json",
    "process_exited": "telemetry-process-exited-1.0.0.schema.json",
    "network_connection_observed": "telemetry-network-connection-observed-1.0.0.schema.json",
}
VALID_FIXTURES = (
    "valid-process-started.json",
    "valid-process-exited.json",
    "valid-network-connection-observed.json",
)
INVALID_FIXTURES = (
    "invalid-extra-field.json",
    "invalid-basis.json",
    "invalid-content-class.json",
    "invalid-identifier.json",
    "oversized-field.json",
)
FORBIDDEN_PACKAGE_TOKENS = (
    "subprocess",
    "os.system",
    "shell=True",
    "eval(",
    "exec(",
    "socket",
    "requests",
    "httpx",
    "sqlalchemy",
    "psycopg",
    "open(",
    "pathlib",
    "os.environ",
)


def _registry() -> Registry:
    registry: Registry = Registry()
    for path in SCHEMAS.glob("*.schema.json"):
        contents = json.loads(path.read_text(encoding="utf-8"))
        registry = registry.with_resource(contents["$id"], Resource.from_contents(contents))
    return registry


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _started() -> dict:
    return _load("valid-process-started.json")


def _exited() -> dict:
    return _load("valid-process-exited.json")


def _network() -> dict:
    return _load("valid-network-connection-observed.json")


def assert_accepted(document: dict) -> TelemetryEnvelope:
    _validator(ENVELOPE_NAME).validate(document)
    _validator(PAYLOAD_SCHEMAS[document["event_type"]]).validate(document["payload"])
    model = TelemetryEnvelope.model_validate(document)
    rendered = model.model_dump(mode="json")
    _validator(ENVELOPE_NAME).validate(rendered)
    return model


def assert_rejected(document: dict) -> None:
    schema_errors = list(_validator(ENVELOPE_NAME).iter_errors(document))
    model_failed = False
    try:
        TelemetryEnvelope.model_validate(document)
    except ValidationError:
        model_failed = True
    assert schema_errors, "JSON Schema accepted a document the model must also reject"
    assert model_failed, "Python model accepted a document the schema must also reject"


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_valid_fixtures_match_schema_and_model(name: str) -> None:
    model = assert_accepted(_load(name))
    assert model.schema_version == SCHEMA_VERSION
    assert model.basis == BASIS
    assert model.content_class == CONTENT_CLASS
    assert model.event_type in EVENT_TYPES


@pytest.mark.parametrize("name", INVALID_FIXTURES)
def test_invalid_fixtures_are_rejected_by_schema_and_model(name: str) -> None:
    assert_rejected(_load(name))


def test_redacted_comm_and_unmapped_network_pid_are_valid() -> None:
    started = _started()
    started["payload"]["comm"] = REDACTED_COMM
    assert_accepted(started)
    network = _network()
    network["payload"]["pid"] = None
    network["payload"]["protocol"] = "udp6"
    network["payload"]["local_port"] = 0
    network["payload"]["remote_port"] = 0
    model = assert_accepted(network)
    assert model.payload.pid is None
    assert model.payload.remote_address == REDACTED_ADDRESS


def test_command_looking_task_name_stays_data() -> None:
    document = _started()
    document["payload"]["comm"] = "reboot"
    model = assert_accepted(document)
    assert model.payload.comm == "reboot"
    assert not hasattr(model, "command")
    assert not hasattr(model.payload, "command")
    document["payload"]["command"] = "reboot"
    assert_rejected(document)


def test_payload_must_match_event_type() -> None:
    document = _started()
    document["payload"] = {"pid": 4242, "start_ticks": 123456}
    assert_rejected(document)


@pytest.mark.parametrize(
    "field",
    [
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
    ],
)
def test_missing_envelope_field_is_rejected(field: str) -> None:
    document = _started()
    del document[field]
    assert_rejected(document)


@pytest.mark.parametrize(
    ("fixture", "field"),
    [
        ("valid-process-started.json", "pid"),
        ("valid-process-started.json", "ppid"),
        ("valid-process-started.json", "uid"),
        ("valid-process-started.json", "start_ticks"),
        ("valid-process-started.json", "comm"),
        ("valid-process-exited.json", "pid"),
        ("valid-process-exited.json", "start_ticks"),
        ("valid-network-connection-observed.json", "protocol"),
        ("valid-network-connection-observed.json", "local_port"),
        ("valid-network-connection-observed.json", "remote_port"),
        ("valid-network-connection-observed.json", "remote_address"),
        ("valid-network-connection-observed.json", "uid"),
        ("valid-network-connection-observed.json", "pid"),
    ],
)
def test_missing_payload_field_is_rejected(fixture: str, field: str) -> None:
    document = _load(fixture)
    del document["payload"][field]
    assert_rejected(document)
    with pytest.raises(SchemaValidationError):
        _validator(PAYLOAD_SCHEMAS[document["event_type"]]).validate(document["payload"])


@pytest.mark.parametrize(
    "event_type",
    [
        "process_modified",
        "file_created",
        "command_executed",
        "login",
        "vulnerability_found",
        "remediation",
        "patch_applied",
    ],
)
def test_unknown_event_type_is_rejected(event_type: str) -> None:
    document = _started()
    document["event_type"] = event_type
    assert_rejected(document)


@pytest.mark.parametrize("basis", ["ebpf", "kernel_hook", "auditd", "tracepoint", "procfs", ""])
def test_wrong_basis_is_rejected(basis: str) -> None:
    document = _started()
    document["basis"] = basis
    assert_rejected(document)


@pytest.mark.parametrize(
    "content_class",
    ["command", "instruction", "action", "remediation", "execution", "observed", ""],
)
def test_wrong_content_class_is_rejected(content_class: str) -> None:
    document = _started()
    document["content_class"] = content_class
    assert_rejected(document)


@pytest.mark.parametrize("version", ["latest", "1.0.1", "2.0.0", "1.0", ""])
def test_unknown_schema_version_is_rejected(version: str) -> None:
    document = _started()
    document["schema_version"] = version
    assert_rejected(document)


@pytest.mark.parametrize("field", ["event_id", "target_id", "agent_id", "boot_id"])
@pytest.mark.parametrize(
    "value",
    [
        "",
        "11111111-1111-4111-8111-111111111111\n",
        "11111111-1111-4111-8111-111111111111\r",
        "11111111-1111-4111-8111-11111111111\x00",
        "11111111-1111-1111-8111-111111111111",
        "11111111111141118111111111111111",
        "11111111-1111-4111-8111-111111111111 ",
        "NOT-A-UUID",
    ],
)
def test_bad_identifiers_are_rejected(field: str, value: str) -> None:
    document = _started()
    document[field] = value
    assert_rejected(document)


def test_oversized_identifier_and_string_are_rejected() -> None:
    document = _started()
    document["event_id"] = "a" * 10000
    assert_rejected(document)
    document = _started()
    document["payload"]["comm"] = "a" * 10000
    assert_rejected(document)
    document = _started()
    document["observed_at"] = "2026-09-29T17:34:00.000000Z" + (" " * 1000)
    assert_rejected(document)


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-09-29T17:34:00",
        "2026-09-29T17:34:00.000000",
        "2026-09-29T17:34:00+00:00",
        "2026-09-29T17:34:00.000000+00:00",
        "2026-09-29t17:34:00.000000Z",
        "2026-09-29T17:34:00.000000z",
        "2026-09-29 17:34:00.000000Z",
        "yesterday",
        "2026-13-29T17:34:00.000000Z",
        "2026-09-29T25:34:00.000000Z",
        "2026-09-29T17:34:00.0000000Z",
    ],
)
def test_invalid_or_naive_timestamps_are_rejected(timestamp: str) -> None:
    document = _started()
    document["observed_at"] = timestamp
    assert_rejected(document)


def test_impossible_calendar_date_is_rejected_by_the_model() -> None:
    """The schema pattern allows February 31. The model rejects that civil date."""
    document = _started()
    document["observed_at"] = "2026-02-31T00:00:00.000000Z"
    _validator(ENVELOPE_NAME).validate(document)
    with pytest.raises(ValidationError):
        TelemetryEnvelope.model_validate(document)


@pytest.mark.parametrize("sequence", [0, -1, -5, 2**63, True, 1.5, "1", None, [1]])
def test_invalid_sequence_is_rejected(sequence: object) -> None:
    document = _started()
    document["sequence"] = sequence
    assert_rejected(document)


def test_maximum_sequence_is_valid() -> None:
    document = _started()
    document["sequence"] = SEQUENCE_MAX
    assert_accepted(document)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pid", 0),
        ("pid", -1),
        ("pid", PID_MAX + 1),
        ("pid", True),
        ("pid", 1.5),
        ("pid", "4242"),
        ("ppid", -1),
        ("ppid", PID_MAX + 1),
        ("uid", -1),
        ("uid", UID_MAX + 1),
        ("start_ticks", -1),
        ("start_ticks", START_TICKS_MAX + 1),
        ("comm", ""),
        ("comm", "a" * (COMM_MAX_LENGTH + 1)),
        ("comm", "/bin/sh"),
        ("comm", "has space"),
        ("comm", "py\nth"),
        ("comm", "py\rth"),
        ("comm", "*"),
        ("comm", "[Redacted]"),
    ],
)
def test_invalid_process_fields_are_rejected(field: str, value: object) -> None:
    document = _started()
    document["payload"][field] = value
    assert_rejected(document)
    with pytest.raises(SchemaValidationError):
        _validator(PAYLOAD_SCHEMAS["process_started"]).validate(document["payload"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("protocol", "icmp"),
        ("protocol", "TCP"),
        ("protocol", "raw"),
        ("local_port", -1),
        ("local_port", PORT_MAX + 1),
        ("local_port", 1.2),
        ("remote_port", -1),
        ("remote_port", 65536),
        ("remote_address", "192.0.2.1"),
        ("remote_address", "10.0.0.1"),
        ("remote_address", "::1"),
        ("remote_address", "*"),
        ("remote_address", "[IP]"),
        ("uid", -1),
        ("pid", 0),
        ("pid", -1),
        ("pid", PID_MAX + 1),
        ("pid", "4242"),
    ],
)
def test_invalid_network_fields_are_rejected(field: str, value: object) -> None:
    document = _network()
    document["payload"][field] = value
    assert_rejected(document)
    with pytest.raises(SchemaValidationError):
        _validator(PAYLOAD_SCHEMAS["network_connection_observed"]).validate(document["payload"])


@pytest.mark.parametrize(
    "key",
    [
        "command",
        "shell",
        "script",
        "execution",
        "action",
        "mitigation",
        "argv",
        "cmdline",
        "environ",
        "password",
        "token",
        "secret",
        "content",
    ],
)
def test_forbidden_keys_are_rejected(key: str) -> None:
    document = _started()
    document[key] = "id"
    assert_rejected(document)
    document = _started()
    document["payload"][key] = "id"
    assert_rejected(document)
    document = _exited()
    document["payload"][key] = {"nested": True}
    assert_rejected(document)


def test_unexpected_nested_objects_and_arrays_are_rejected() -> None:
    document = _started()
    document["payload"]["pid"] = {"command": "id"}
    assert_rejected(document)
    document = _started()
    document["payload"] = [{"pid": 1}]
    assert_rejected(document)
    document = _started()
    document["sequence"] = [1]
    assert_rejected(document)
    document = _network()
    document["payload"]["remote_address"] = {"value": "[ip]"}
    assert_rejected(document)
    document = _started()
    document["target_id"] = ["22222222-2222-4222-8222-222222222222"]
    assert_rejected(document)


def test_exit_payload_cannot_carry_an_exit_code() -> None:
    document = _exited()
    document["payload"]["exit_code"] = 0
    assert_rejected(document)


def test_bounds_and_patterns_match_the_schemas() -> None:
    envelope = _schema(ENVELOPE_NAME)
    started = _schema(PAYLOAD_SCHEMAS["process_started"])
    network = _schema(PAYLOAD_SCHEMAS["network_connection_observed"])
    assert envelope["x-synapse-contract-version"] == "1.0.0"
    assert envelope["additionalProperties"] is False
    assert envelope["properties"]["sequence"]["minimum"] == 1
    assert envelope["properties"]["sequence"]["maximum"] == SEQUENCE_MAX
    assert envelope["properties"]["event_type"]["enum"] == list(EVENT_TYPES)
    assert envelope["properties"]["basis"]["const"] == BASIS
    assert envelope["properties"]["content_class"]["const"] == CONTENT_CLASS
    assert envelope["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    assert envelope["properties"]["event_id"]["pattern"] == UUID_V4_PATTERN
    assert envelope["properties"]["observed_at"]["pattern"] == TIMESTAMP_PATTERN
    assert started["properties"]["pid"]["maximum"] == PID_MAX
    assert started["properties"]["uid"]["maximum"] == UID_MAX
    assert started["properties"]["start_ticks"]["maximum"] == START_TICKS_MAX
    assert started["properties"]["comm"]["maxLength"] == COMM_MAX_LENGTH
    assert started["properties"]["comm"]["pattern"] == COMM_PATTERN
    assert started["additionalProperties"] is False
    assert network["properties"]["local_port"]["maximum"] == PORT_MAX
    assert network["properties"]["remote_address"]["const"] == REDACTED_ADDRESS
    assert network["additionalProperties"] is False
    for name in (ENVELOPE_NAME, *PAYLOAD_SCHEMAS.values()):
        schema = _schema(name)
        assert schema["additionalProperties"] is False
        assert schema["x-synapse-contract-version"] == "1.0.0"


def test_observed_at_matches_the_audit_timestamp_form() -> None:
    model = assert_accepted(_started())
    assert format_observed_at(model.observed_at) == format_timestamp(model.observed_at)
    assert model.model_dump(mode="json")["observed_at"] == "2026-09-29T17:34:00.000000Z"


def test_package_has_no_host_network_or_database_io() -> None:
    offenders: list[str] = []
    python_files = [path for path in PACKAGE.rglob("*.py") if "__pycache__" not in path.parts]
    assert sorted(path.name for path in python_files) == [
        "__init__.py",
        "canonical.py",
        "envelope.py",
        "signatures.py",
    ]
    for path in python_files:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_PACKAGE_TOKENS:
            if token in text:
                offenders.append(f"{path.name} contains {token}")
    assert offenders == []
