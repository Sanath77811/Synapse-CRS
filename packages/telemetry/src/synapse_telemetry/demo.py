"""Offline terminal demonstration of Phase 1 contracts and Phase 2 signatures."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TextIO

from synapse_telemetry.demo_runner import DemoReport, run_demonstration
from synapse_telemetry.signatures import SIGNATURE_LENGTH

PROJECT = "SYNAPSE-CRS"
SUBTITLE = "Neuro-Symbolic Cyber Reasoning System"
VERSION = "v0.2"
WIDTH = 72


def _line(stream: TextIO, text: str = "") -> None:
    stream.write(text + "\n")


def _rule(stream: TextIO, char: str = "=") -> None:
    _line(stream, char * WIDTH)


def _banner(stream: TextIO) -> None:
    _rule(stream)
    _line(stream, f" {PROJECT}")
    _line(stream, f" {SUBTITLE}")
    _line(stream, f" Version {VERSION}  |  Offline telemetry security demonstrator")
    _line(stream, " Events are synthetic laboratory observations, not live host data.")
    _rule(stream)


def _stage(stream: TextIO, number: int, title: str) -> None:
    _line(stream)
    _rule(stream, "-")
    _line(stream, f" Stage {number} — {title}")
    _rule(stream, "-")


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _rejected(ok: bool) -> str:
    return "REJECTED" if ok else "FAIL (accepted)"


def render_report(report: DemoReport, stream: TextIO) -> None:
    """Write a readable terminal summary of one measured demonstration."""
    _banner(stream)

    _stage(stream, 1, "Telemetry event generation")
    _line(stream, f" Label: {report.laboratory_label}")
    _line(stream, f" Events generated: {report.events_generated}")
    for event in report.events:
        _line(
            stream,
            f"  - type={event['event_type']}  id={event['event_id']}  sequence={event['sequence']}",
        )
    _line(stream, f" Result: {_status(report.events_generated == 3)}")

    _stage(stream, 2, "Strict schema validation")
    for row in report.validation_rows:
        _line(
            stream,
            "  - "
            f"type={row.event_type}  "
            f"event_id={row.event_id}  "
            f"target_id={row.target_id}  "
            f"agent_id={row.agent_id}  "
            f"sequence={row.sequence}  "
            f"validation={_status(row.accepted)}",
        )
    invalid_id = report.invalid_event["event_id"] if report.invalid_event else "missing"
    _line(
        stream,
        "  - "
        f"invalid document event_id={invalid_id}  "
        f"reason={report.invalid_detail or 'not rejected'}  "
        f"validation={_rejected(report.invalid_rejected)}",
    )
    _line(
        stream,
        f" Result: {_status(report.events_accepted == 3 and report.invalid_rejected)}",
    )

    _stage(stream, 3, "Cryptographic key generation")
    _line(stream, f" Algorithm: {report.algorithm}")
    _line(stream, f" Public key fingerprint: {report.public_key_fingerprint}")
    _line(stream, " Private key: held in memory, not displayed, not written to disk")
    _line(stream, f" Result: {_status(bool(report.public_key_fingerprint))}")

    _stage(stream, 4, "Event signing")
    _line(stream, f" Signature algorithm: {report.algorithm}")
    _line(stream, f" Expected raw signature length: {SIGNATURE_LENGTH} bytes")
    for row in report.signed_rows:
        _line(
            stream,
            "  - "
            f"event_id={row.event_id}  "
            f"type={row.event_type}  "
            f"raw_length={row.raw_length}  "
            f"encoding=standard-base64  "
            f"signing={_status(row.signed)}",
        )
        _line(stream, f"    signature={row.signature}")
    _line(stream, f" Result: {_status(report.events_signed == 3)}")

    _stage(stream, 5, "Signature verification")
    for row, verified in zip(report.signed_rows, report.verified_original, strict=False):
        _line(
            stream,
            f"  - event_id={row.event_id}  verification={_status(verified)}",
        )
    _line(stream, f" Result: {_status(report.signatures_verified == 3)}")

    _stage(stream, 6, "Tampering attack demonstration")
    _line(
        stream,
        f" Original event integrity: "
        f"{'VALID' if report.original_still_valid_after_tamper else 'FAIL'}",
    )
    _line(
        stream,
        f" Modified payload integrity: {'REJECTED' if report.payload_tamper_rejected else 'FAIL'}",
    )
    _line(
        stream,
        f" Modified identity integrity: "
        f"{'REJECTED' if report.identity_tamper_rejected else 'FAIL'}",
    )
    _line(
        stream,
        f" Original events unchanged: {_status(report.original_unchanged)}",
    )
    tamper_ok = report.tampering_attempts_detected == 2 and report.original_unchanged
    _line(stream, f" Result: {_status(tamper_ok)}")

    _stage(stream, 7, "Final security summary")
    _line(stream, f" Synthetic events generated: {report.events_generated}")
    _line(stream, f" Events accepted by schema validation: {report.events_accepted}")
    _line(stream, f" Invalid events rejected: {report.invalid_events_rejected}")
    _line(stream, f" Events successfully signed: {report.events_signed}")
    _line(stream, f" Signatures successfully verified: {report.signatures_verified}")
    _line(stream, f" Tampering attempts detected: {report.tampering_attempts_detected}")
    _line(stream)
    if report.succeeded:
        _line(stream, " Demonstration result: PASS")
        _line(stream, " A valid signature proves key possession only, not authorization.")
    else:
        _line(stream, " Demonstration result: FAIL")
        _line(stream, f" Failure: {report.failure or 'required stage did not succeed'}")
    _rule(stream)


def main(argv: Sequence[str] | None = None, stream: TextIO | None = None) -> int:
    """Run the demonstration and return 0 only when every required stage passes."""
    del argv
    output = sys.stdout if stream is None else stream
    report = run_demonstration()
    render_report(report, output)
    return 0 if report.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
