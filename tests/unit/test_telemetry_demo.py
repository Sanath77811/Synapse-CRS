"""The offline demonstrator must call the real Phase 1 and Phase 2 APIs."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from synapse_telemetry.demo import main
from synapse_telemetry.demo_data import invalid_synthetic_event, synthetic_events
from synapse_telemetry.demo_runner import DemoReport, run_demonstration
from synapse_telemetry.envelope import EVENT_TYPES, TelemetryEnvelope
from synapse_telemetry.signatures import (
    SIGNATURE_LENGTH,
    SignatureError,
    decode_signature,
    generate_signing_key,
    verify_event,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "packages" / "telemetry" / "src"


def test_synthetic_events_are_valid_phase1_documents() -> None:
    events = synthetic_events()
    assert len(events) == 3
    types = {event["event_type"] for event in events}
    assert types == set(EVENT_TYPES)
    for event in events:
        TelemetryEnvelope.model_validate(event)


def test_invalid_synthetic_event_is_rejected_by_the_real_validator() -> None:
    invalid = invalid_synthetic_event()
    assert "command" in invalid
    with pytest.raises(ValidationError):
        TelemetryEnvelope.model_validate(invalid)


def test_demonstration_signs_and_verifies_with_ed25519() -> None:
    report = run_demonstration()
    assert report.succeeded is True
    assert report.algorithm == "Ed25519"
    assert report.public_key_fingerprint.startswith("sha256:")
    assert len(report.public_key_fingerprint) == len("sha256:") + 64
    assert report.events_signed == 3
    for row in report.signed_rows:
        assert row.raw_length == SIGNATURE_LENGTH
        assert len(decode_signature(row.signature)) == SIGNATURE_LENGTH
    assert report.signatures_verified == 3
    key = generate_signing_key().public_key()
    with pytest.raises(SignatureError):
        verify_event(key, report.events[0], report.signed_rows[0].signature)


def test_payload_and_identity_tampering_are_rejected() -> None:
    report = run_demonstration()
    assert report.payload_tamper_rejected is True
    assert report.identity_tamper_rejected is True
    assert report.original_still_valid_after_tamper is True
    assert report.original_unchanged is True
    assert report.tampering_attempts_detected == 2


def test_original_events_remain_unchanged_after_the_run() -> None:
    report = run_demonstration()
    assert report.original_unchanged is True
    snapshots = [json.dumps(event, sort_keys=True) for event in report.events]
    for event, row in zip(report.events, report.signed_rows, strict=True):
        TelemetryEnvelope.model_validate(event)
        assert "signature" not in event
        assert event["event_id"] == row.event_id
    mutated = json.loads(snapshots[0])
    mutated["target_id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    assert json.dumps(report.events[0], sort_keys=True) == snapshots[0]
    assert mutated["target_id"] != report.events[0]["target_id"]


def test_summary_counters_match_measured_results() -> None:
    report = run_demonstration()
    assert report.events_generated == len(report.events) == 3
    assert report.events_accepted == sum(1 for row in report.validation_rows if row.accepted)
    assert report.invalid_events_rejected == 1
    assert report.events_signed == sum(1 for row in report.signed_rows if row.signed)
    assert report.signatures_verified == sum(1 for item in report.verified_original if item)
    assert report.tampering_attempts_detected == 2
    failed = DemoReport()
    assert failed.succeeded is False
    assert failed.events_generated == 0
    assert failed.signatures_verified == 0


def test_failed_verification_is_not_reported_as_success() -> None:
    report = DemoReport()
    report.verified_original = [True, False, True]
    assert report.signatures_verified == 2
    report.payload_tamper_rejected = False
    report.identity_tamper_rejected = True
    assert report.tampering_attempts_detected == 1
    assert report.succeeded is False


def test_private_key_material_is_absent_from_terminal_output() -> None:
    buffer = io.StringIO()
    status = main([], stream=buffer)
    output = buffer.getvalue()
    assert status == 0
    assert "Demonstration result: PASS" in output
    assert "Modified payload integrity: REJECTED" in output
    assert "Modified identity integrity: REJECTED" in output
    assert "Original event integrity: VALID" in output
    assert "SigningKey" not in output
    assert "_private" not in output
    assert "BEGIN" not in output
    assert "private key" in output.lower()
    lowered = output.lower()
    assert "private_bytes" not in lowered
    assert "ed25519privatekey" not in lowered


def test_cli_module_runs_successfully() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PACKAGE)
    completed = subprocess.run(
        [sys.executable, "-m", "synapse_telemetry.demo"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "SYNAPSE-CRS" in completed.stdout
    assert "Neuro-Symbolic Cyber Reasoning System" in completed.stdout
    assert "Demonstration result: PASS" in completed.stdout
    assert "FAIL" not in completed.stdout
    assert completed.stderr == ""
