"""Published JSON Schemas accept the same examples as the pydantic contracts."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError
from referencing import Registry, Resource
from synapse_contracts.agents import AgentEnroll
from synapse_contracts.cases import CaseCreate, CaseTransitionRequest
from synapse_contracts.errors import ErrorResponse
from synapse_contracts.targets import TargetCreate
from synapse_contracts.telemetry_ingest import TelemetryIngestRequest

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "tests" / "fixtures" / "contracts"


def schema_registry() -> Registry:
    registry: Registry = Registry()
    for path in SCHEMAS.glob("*.schema.json"):
        contents = json.loads(path.read_text(encoding="utf-8"))
        registry = registry.with_resource(contents["$id"], Resource.from_contents(contents))
    return registry


@pytest.mark.parametrize(
    ("schema_name", "model"),
    [
        ("target-create-1.0.0.schema.json", TargetCreate),
        ("case-create-1.0.0.schema.json", CaseCreate),
        ("case-transition-request-1.0.0.schema.json", CaseTransitionRequest),
        ("error-1.0.0.schema.json", ErrorResponse),
    ],
)
def test_examples_match_schema_and_model(schema_name: str, model: type) -> None:
    schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    example_name = schema_name.replace(".schema.json", ".json")
    example = json.loads((EXAMPLES / example_name).read_text(encoding="utf-8"))
    Draft202012Validator(
        schema,
        registry=schema_registry(),
        format_checker=FormatChecker(),
    ).validate(example)
    assert schema["x-synapse-contract-version"] == "1.0.0"
    if model is ErrorResponse:
        model.model_validate(example)
    else:
        model.model_validate(example)


def test_contract_models_reject_unknown_fields() -> None:
    example = json.loads((EXAMPLES / "target-create-1.0.0.json").read_text(encoding="utf-8"))
    example["actor"] = "spoofed"
    with pytest.raises(ValidationError):
        TargetCreate.model_validate(example)


def test_scope_schema_rejects_unbounded_asset() -> None:
    schema = json.loads((SCHEMAS / "target-scope-1.0.0.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    rejected = {
        "environment": "lab",
        "assets": ["*"],
        "description": "Unbounded scope.",
    }
    errors = list(validator.iter_errors(rejected))
    assert errors
    with pytest.raises(ValidationError):
        from synapse_contracts.scope import TargetScope

        TargetScope.model_validate(rejected)


def test_agent_enroll_rejects_private_key_fields() -> None:
    body = {"public_key_hex": "ab" * 32, "private_key_hex": "cd" * 32}
    with pytest.raises(ValidationError):
        AgentEnroll.model_validate(body)
    AgentEnroll.model_validate({"public_key_hex": "ab" * 32})


def test_ingest_request_rejects_trust_labels() -> None:
    envelope = {
        "schema_version": "1.0.0",
        "event_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "target_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "agent_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "boot_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "event_type": "process_started",
        "sequence": 1,
        "observed_at": "2026-09-29T17:34:00.000000Z",
        "basis": "procfs_poll",
        "content_class": "observation",
        "payload": {
            "pid": 1,
            "ppid": 1,
            "uid": 0,
            "start_ticks": 1,
            "comm": "python3",
        },
    }
    signature = "A" * 86 + "=="
    TelemetryIngestRequest.model_validate({"envelope": envelope, "signature": signature})
    for extra in (
        {"verified": True},
        {"identity_status": "authorized"},
        {"public_key_hex": "ab" * 32},
    ):
        body = {"envelope": envelope, "signature": signature, **extra}
        with pytest.raises(ValidationError):
            TelemetryIngestRequest.model_validate(body)
