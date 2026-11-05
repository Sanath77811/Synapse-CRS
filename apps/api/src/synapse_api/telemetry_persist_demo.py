"""Database-backed telemetry evidence demonstration.

Requires DATABASE_URL for synapse_app. This is not the offline demo.
It does not enroll agents or start the HTTP API.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TextIO
from uuid import uuid4

from sqlalchemy.orm import sessionmaker
from synapse_telemetry.demo_data import laboratory_clock, laboratory_identity
from synapse_telemetry.normalization import normalize_observation
from synapse_telemetry.signatures import generate_signing_key, sign_event

from synapse_api.db import get_engine
from synapse_api.telemetry_store import PersistenceError, persist_verified_event

WIDTH = 72


def _line(stream: TextIO, text: str = "") -> None:
    stream.write(text + "\n")


def main(argv: Sequence[str] | None = None, stream: TextIO | None = None) -> int:
    del argv
    output = sys.stdout if stream is None else stream
    _line(output, "=" * WIDTH)
    _line(output, " SYNAPSE-CRS")
    _line(output, " Telemetry evidence persistence demonstration")
    _line(output, " Requires PostgreSQL. Identity remains unverified.")
    _line(output, "=" * WIDTH)
    try:
        engine = get_engine()
        session = sessionmaker(autoflush=False, expire_on_commit=False)(bind=engine)
    except Exception as exc:
        _line(output, " Result: FAIL")
        _line(
            output,
            f" Could not open the application database. error_type={type(exc).__name__}",
        )
        return 1
    identity = laboratory_identity()
    stamp = laboratory_clock()
    raw = {
        "event_type": "process_started",
        "target_id": identity["target_id"],
        "agent_id": identity["agent_id"],
        "boot_id": identity["boot_id"],
        "sequence": 1,
        "observed_at": stamp,
        "event_id": str(uuid4()),
        "pid": 4242,
        "ppid": 1,
        "uid": 1000,
        "start_ticks": 123456,
        "comm": "python3",
        "argv": ["python3", "--version"],
    }
    try:
        envelope = normalize_observation(raw)
        _line(output, " Normalized: PASS")
        key = generate_signing_key()
        signature = sign_event(key, envelope)
        _line(output, " Schema validated and signed: PASS")
        first = persist_verified_event(session, envelope, signature, key.public_key())
        session.commit()
        _line(output, f" Evidence persisted: {first.status.upper()}")
        _line(output, f" Identity status: {first.record.identity_status}")
        _line(output, f" Signature verified: {first.record.signature_verified}")
        duplicate = persist_verified_event(session, envelope, signature, key.public_key())
        session.commit()
        _line(output, f" Exact duplicate: {duplicate.status.upper()}")
        replay = envelope.model_dump(mode="json")
        replay["event_id"] = str(uuid4())
        replay_signature = sign_event(key, replay)
        try:
            persist_verified_event(session, replay, replay_signature, key.public_key())
            session.commit()
            _line(output, " Sequence replay: FAIL (accepted)")
            return 1
        except PersistenceError as exc:
            session.rollback()
            if exc.code != "sequence_conflict":
                _line(output, f" Sequence replay: FAIL ({exc.code})")
                return 1
            _line(output, " Sequence replay: REJECTED")
        if first.status != "stored" or duplicate.status != "duplicate":
            _line(output, " Result: FAIL")
            return 1
        _line(output, " Demonstration result: PASS")
        return 0
    except Exception as exc:
        session.rollback()
        _line(output, " Demonstration result: FAIL")
        _line(output, f" Failure: {type(exc).__name__}")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
