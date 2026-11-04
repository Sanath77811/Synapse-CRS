"""Orchestrate the offline telemetry security demonstration.

Each stage calls the Phase 1 validator or the Phase 2 signing API. A stage
that does not observe the required outcome is recorded as a failure. The
runner never treats an unexpected exception as success.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from pydantic import ValidationError

from synapse_telemetry.demo_data import (
    LABORATORY_LABEL,
    invalid_synthetic_event,
    new_uuid4,
    synthetic_raw_observations,
)
from synapse_telemetry.envelope import REDACTED_ADDRESS, TelemetryEnvelope
from synapse_telemetry.normalization import discarded_keys, normalize_observation
from synapse_telemetry.signatures import (
    SIGNATURE_LENGTH,
    SignatureError,
    SigningKey,
    VerificationKey,
    decode_signature,
    generate_signing_key,
    sign_event,
    verify_event,
)


@dataclass(frozen=True)
class ValidationRow:
    event_type: str
    event_id: str
    target_id: str
    agent_id: str
    sequence: int
    accepted: bool
    detail: str


@dataclass(frozen=True)
class NormalizationRow:
    event_type: str
    discarded: tuple[str, ...]
    remote_address: str | None
    address_redacted: bool


@dataclass(frozen=True)
class SignedRow:
    event_id: str
    event_type: str
    signature: str
    raw_length: int
    signed: bool


@dataclass
class DemoReport:
    """Measured outcomes from one demonstration run."""

    succeeded: bool = False
    laboratory_label: str = LABORATORY_LABEL
    raw_observations: list[dict[str, object]] = field(default_factory=list)
    normalization_rows: list[NormalizationRow] = field(default_factory=list)
    events: list[dict[str, object]] = field(default_factory=list)
    validation_rows: list[ValidationRow] = field(default_factory=list)
    invalid_event: dict[str, object] | None = None
    invalid_rejected: bool = False
    invalid_detail: str = ""
    algorithm: str = "Ed25519"
    public_key_fingerprint: str = ""
    signed_rows: list[SignedRow] = field(default_factory=list)
    verified_original: list[bool] = field(default_factory=list)
    original_still_valid_after_tamper: bool = False
    payload_tamper_rejected: bool = False
    identity_tamper_rejected: bool = False
    original_unchanged: bool = False
    failure: str | None = None

    @property
    def events_generated(self) -> int:
        return len(self.events)

    @property
    def observations_normalized(self) -> int:
        return len(self.normalization_rows)

    @property
    def addresses_redacted(self) -> int:
        return sum(1 for row in self.normalization_rows if row.address_redacted)

    @property
    def extra_fields_discarded(self) -> int:
        return sum(len(row.discarded) for row in self.normalization_rows)

    @property
    def events_accepted(self) -> int:
        return sum(1 for row in self.validation_rows if row.accepted)

    @property
    def invalid_events_rejected(self) -> int:
        return 1 if self.invalid_rejected else 0

    @property
    def events_signed(self) -> int:
        return sum(1 for row in self.signed_rows if row.signed)

    @property
    def signatures_verified(self) -> int:
        return sum(1 for item in self.verified_original if item)

    @property
    def tampering_attempts_detected(self) -> int:
        return int(self.payload_tamper_rejected) + int(self.identity_tamper_rejected)


def public_key_fingerprint(key: VerificationKey) -> str:
    """Return a SHA-256 fingerprint of the 32-byte public key."""
    digest = hashlib.sha256(key.raw_bytes()).hexdigest()
    return f"sha256:{digest}"


def _snapshot(event: dict[str, object]) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"))


def _copy(event: dict[str, object]) -> dict[str, object]:
    copied = json.loads(json.dumps(event))
    if not isinstance(copied, dict):
        raise TypeError("event copy must be an object")
    return copied


def _require_signature_error(
    key: VerificationKey, event: dict[str, object], signature: str
) -> bool:
    try:
        verify_event(key, event, signature)
    except SignatureError:
        return True
    except ValidationError:
        return False
    return False


def run_demonstration() -> DemoReport:
    """Run every demonstration stage against the real contracts and signer."""
    report = DemoReport()
    try:
        raw_observations = synthetic_raw_observations()
        report.raw_observations = raw_observations
        raw_snapshots = [_snapshot(item) for item in raw_observations]
        events: list[dict[str, object]] = []
        for raw in raw_observations:
            event_type = str(raw["event_type"])
            extras = discarded_keys(raw, event_type)
            envelope = normalize_observation(raw)
            document = envelope.model_dump(mode="json")
            payload = document["payload"]
            remote = payload.get("remote_address") if isinstance(payload, dict) else None
            report.normalization_rows.append(
                NormalizationRow(
                    event_type=event_type,
                    discarded=extras,
                    remote_address=str(remote) if remote is not None else None,
                    address_redacted=remote == REDACTED_ADDRESS,
                )
            )
            events.append(document)
        report.events = events
        if [_snapshot(item) for item in raw_observations] != raw_snapshots:
            report.failure = "raw observations were mutated"
            return report
        if len(events) != 3:
            report.failure = "normalization did not produce three events"
            return report
        if report.addresses_redacted < 1:
            report.failure = "network address was not redacted to [ip]"
            return report
        if report.extra_fields_discarded < 1:
            report.failure = "unsupported fields were not discarded"
            return report
        dumped = json.dumps(events)
        if "192.0.2.10" in dumped or "/usr/bin/python3" in dumped:
            report.failure = "sensitive raw values remained after normalization"
            return report

        for event in events:
            document = TelemetryEnvelope.model_validate(event).model_dump(mode="json")
            report.validation_rows.append(
                ValidationRow(
                    event_type=str(document["event_type"]),
                    event_id=str(document["event_id"]),
                    target_id=str(document["target_id"]),
                    agent_id=str(document["agent_id"]),
                    sequence=int(document["sequence"]),
                    accepted=True,
                    detail="accepted by TelemetryEnvelope",
                )
            )
        if report.events_accepted != 3:
            report.failure = "a synthetic event was not accepted"
            return report

        invalid = invalid_synthetic_event()
        report.invalid_event = invalid
        try:
            TelemetryEnvelope.model_validate(invalid)
        except ValidationError as exc:
            report.invalid_rejected = True
            report.invalid_detail = exc.errors()[0]["type"]
        else:
            report.failure = "invalid event was accepted"
            return report

        signing_key: SigningKey = generate_signing_key()
        verification_key = signing_key.public_key()
        report.public_key_fingerprint = public_key_fingerprint(verification_key)
        if str(signing_key) != "SigningKey(redacted)":
            report.failure = "private key representation is not redacted"
            return report

        originals = [_snapshot(event) for event in events]
        for event in events:
            signature = sign_event(signing_key, event)
            raw = decode_signature(signature)
            report.signed_rows.append(
                SignedRow(
                    event_id=str(event["event_id"]),
                    event_type=str(event["event_type"]),
                    signature=signature,
                    raw_length=len(raw),
                    signed=len(raw) == SIGNATURE_LENGTH,
                )
            )
        if report.events_signed != 3:
            report.failure = "signing did not produce three Ed25519 signatures"
            return report

        for event, row in zip(events, report.signed_rows, strict=True):
            verify_event(verification_key, event, row.signature)
            report.verified_original.append(True)
        if report.signatures_verified != 3:
            report.failure = "an original signature did not verify"
            return report

        target = events[0]
        target_signature = report.signed_rows[0].signature
        payload_tampered = _copy(target)
        payload = payload_tampered["payload"]
        if not isinstance(payload, dict):
            report.failure = "payload is not an object"
            return report
        payload["comm"] = "nginx"
        report.payload_tamper_rejected = _require_signature_error(
            verification_key, payload_tampered, target_signature
        )
        identity_tampered = _copy(target)
        identity_tampered["target_id"] = new_uuid4()
        report.identity_tamper_rejected = _require_signature_error(
            verification_key, identity_tampered, target_signature
        )
        try:
            verify_event(verification_key, target, target_signature)
            report.original_still_valid_after_tamper = True
        except SignatureError:
            report.original_still_valid_after_tamper = False
        report.original_unchanged = [_snapshot(event) for event in events] == originals

        if not report.payload_tamper_rejected:
            report.failure = "payload tampering was not rejected by verify_event"
            return report
        if not report.identity_tamper_rejected:
            report.failure = "identity tampering was not rejected by verify_event"
            return report
        if not report.original_still_valid_after_tamper:
            report.failure = "original event failed verification after tamper copies"
            return report
        if not report.original_unchanged:
            report.failure = "original events were mutated"
            return report

        report.succeeded = True
        return report
    except Exception as exc:
        report.succeeded = False
        report.failure = f"unexpected {type(exc).__name__}"
        return report
