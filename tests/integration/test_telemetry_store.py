"""PostgreSQL evidence store: verify first, then insert once."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from synapse_api.telemetry_store import (
    PersistenceError,
    get_event_by_id,
    list_events,
    persist_verified_event,
)
from synapse_telemetry.envelope import TelemetryEnvelope
from synapse_telemetry.normalization import normalize_observation
from synapse_telemetry.signatures import generate_signing_key, sign_event

from tests.integration.conftest import ROOT

FIXED_TIME = "2026-09-29T17:34:00.000000Z"


def _session(tokens) -> Session:
    return sessionmaker(autoflush=False, expire_on_commit=False)(
        bind=create_engine(tokens["app_url"])
    )


def _raw(**extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "event_type": "process_started",
        "target_id": str(uuid4()),
        "agent_id": str(uuid4()),
        "boot_id": str(uuid4()),
        "sequence": 1,
        "observed_at": FIXED_TIME,
        "event_id": str(uuid4()),
        "pid": 4242,
        "ppid": 1,
        "uid": 1000,
        "start_ticks": 123456,
        "comm": "python3",
    }
    body.update(extra)
    return body


def _signed(event_type: str = "process_started", **extra: object):
    if event_type == "process_exited":
        extra.setdefault("pid", 4242)
        extra.setdefault("start_ticks", 123456)
        extra.pop("ppid", None)
        extra.pop("uid", None)
        extra.pop("comm", None)
    if event_type == "network_connection_observed":
        extra.setdefault("protocol", "tcp")
        extra.setdefault("local_port", 40000)
        extra.setdefault("remote_port", 443)
        extra.setdefault("remote_address", "192.0.2.10")
        extra.setdefault("uid", 1000)
        extra.setdefault("pid", 4242)
        extra.pop("ppid", None)
        extra.pop("comm", None)
        extra.pop("start_ticks", None)
    envelope = normalize_observation(_raw(event_type=event_type, **extra))
    key = generate_signing_key()
    signature = sign_event(key, envelope)
    return envelope, signature, key


def _count(tokens) -> int:
    engine = create_engine(tokens["app_url"])
    with engine.connect() as connection:
        value = connection.execute(text("SELECT count(*) FROM telemetry_events")).scalar()
    engine.dispose()
    return int(value or 0)


def test_valid_events_are_verified_then_stored(tokens) -> None:
    session = _session(tokens)
    try:
        for event_type in (
            "process_started",
            "process_exited",
            "network_connection_observed",
        ):
            envelope, signature, key = _signed(event_type)
            result = persist_verified_event(session, envelope, signature, key.public_key())
            session.commit()
            assert result.status == "stored"
            assert result.record.signature_verified is True
            assert result.record.identity_status == "unverified"
            assert result.record.event_type == event_type
            assert result.record.signature == signature
            assert result.record.public_key_hex == key.public_key().raw_bytes().hex()
            assert result.record.public_key_fingerprint.startswith("sha256:")
            assert result.record.envelope["event_id"] == str(envelope.event_id)
            assert "argv" not in result.record.envelope
            assert "192.0.2.10" not in str(result.record.envelope)
            loaded = get_event_by_id(session, envelope.event_id)
            assert loaded is not None
            assert loaded.id == result.record.id
            TelemetryEnvelope.model_validate(loaded.envelope)
    finally:
        session.close()


def test_invalid_evidence_does_not_create_a_row(tokens) -> None:
    session = _session(tokens)
    envelope, signature, key = _signed()
    other = generate_signing_key()
    before = _count(tokens)
    try:
        with pytest.raises(PersistenceError) as invalid:
            persist_verified_event(session, {"event_type": "nope"}, signature, key.public_key())
        assert invalid.value.code == "invalid_envelope"
        tampered = envelope.model_dump(mode="json")
        tampered["payload"]["comm"] = "nginx"
        with pytest.raises(PersistenceError) as payload:
            persist_verified_event(session, tampered, signature, key.public_key())
        assert payload.value.code == "invalid_signature"
        identity = envelope.model_dump(mode="json")
        identity["target_id"] = str(uuid4())
        with pytest.raises(PersistenceError) as target:
            persist_verified_event(session, identity, signature, key.public_key())
        assert target.value.code == "invalid_signature"
        agent = envelope.model_dump(mode="json")
        agent["agent_id"] = str(uuid4())
        with pytest.raises(PersistenceError) as agent_err:
            persist_verified_event(session, agent, signature, key.public_key())
        assert agent_err.value.code == "invalid_signature"
        with pytest.raises(PersistenceError) as wrong:
            persist_verified_event(session, envelope, signature, other.public_key())
        assert wrong.value.code == "invalid_signature"
        with pytest.raises(PersistenceError) as missing:
            persist_verified_event(session, envelope, "", key.public_key())
        assert missing.value.code == "invalid_signature"
        with pytest.raises(PersistenceError) as malformed:
            persist_verified_event(session, envelope, "@@@@", key.public_key())
        assert malformed.value.code == "invalid_signature"
        session.rollback()
        assert _count(tokens) == before
    finally:
        session.close()


def test_exact_duplicate_is_idempotent(tokens) -> None:
    session = _session(tokens)
    envelope, signature, key = _signed()
    try:
        first = persist_verified_event(session, envelope, signature, key.public_key())
        session.commit()
        second = persist_verified_event(session, envelope, signature, key.public_key())
        session.commit()
        assert first.status == "stored"
        assert second.status == "duplicate"
        assert second.record.id == first.record.id
        assert _count(tokens) == 1
    finally:
        session.close()


def test_event_id_and_sequence_conflicts_are_rejected(tokens) -> None:
    session = _session(tokens)
    envelope, signature, key = _signed()
    try:
        persist_verified_event(session, envelope, signature, key.public_key())
        session.commit()
        changed_payload = envelope.model_dump(mode="json")
        changed_payload["payload"]["comm"] = "nginx"
        new_signature = sign_event(key, changed_payload)
        with pytest.raises(PersistenceError) as payload:
            persist_verified_event(session, changed_payload, new_signature, key.public_key())
        assert payload.value.code == "event_id_conflict"
        other_key = generate_signing_key()
        other_signature = sign_event(other_key, envelope)
        with pytest.raises(PersistenceError) as other:
            persist_verified_event(session, envelope, other_signature, other_key.public_key())
        assert other.value.code == "event_id_conflict"
        replay = envelope.model_dump(mode="json")
        replay["event_id"] = str(uuid4())
        replay_signature = sign_event(key, replay)
        with pytest.raises(PersistenceError) as sequence:
            persist_verified_event(session, replay, replay_signature, key.public_key())
        assert sequence.value.code == "sequence_conflict"
        session.rollback()
        assert _count(tokens) == 1
        loaded = get_event_by_id(session, envelope.event_id)
        assert loaded is not None
        assert loaded.envelope["payload"]["comm"] == "python3"
    finally:
        session.close()


def test_concurrent_duplicate_insert_keeps_one_row(tokens) -> None:
    envelope, signature, key = _signed()
    barrier = Barrier(2)
    outcomes: list[str] = []

    def worker() -> None:
        session = _session(tokens)
        try:
            barrier.wait(timeout=5)
            result = persist_verified_event(session, envelope, signature, key.public_key())
            session.commit()
            outcomes.append(result.status)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker), pool.submit(worker)]
        for future in futures:
            future.result(timeout=15)
    assert sorted(outcomes) == ["duplicate", "stored"]
    assert _count(tokens) == 1


def test_retrieval_filters_and_pagination(tokens) -> None:
    session = _session(tokens)
    key = generate_signing_key()
    target_a = uuid4()
    target_b = uuid4()
    agent_a = uuid4()
    try:
        stamps = [
            "2026-09-29T17:34:00.000000Z",
            "2026-09-29T17:35:00.000000Z",
            "2026-09-29T17:36:00.000000Z",
        ]
        for index, stamp in enumerate(stamps, start=1):
            envelope = normalize_observation(
                _raw(
                    event_id=str(uuid4()),
                    target_id=str(target_a if index < 3 else target_b),
                    agent_id=str(agent_a),
                    boot_id=str(uuid4()),
                    sequence=index,
                    observed_at=stamp,
                    event_type="process_started" if index != 2 else "process_exited",
                    **({"pid": 4242, "start_ticks": 1} if index == 2 else {}),
                )
            )
            persist_verified_event(session, envelope, sign_event(key, envelope), key.public_key())
        session.commit()
        page = list_events(session, limit=2, offset=0, agent_id=agent_a)
        assert page.total == 3
        assert len(page.items) == 2
        assert page.items[0].observed_at <= page.items[1].observed_at
        second = list_events(session, limit=2, offset=2, agent_id=agent_a)
        assert len(second.items) == 1
        assert {item.event_id for item in page.items + second.items} == {
            item.event_id for item in list_events(session, limit=100, offset=0).items
        }
        filtered = list_events(session, limit=50, offset=0, target_id=target_b)
        assert filtered.total == 1
        typed = list_events(session, limit=50, offset=0, event_type="process_exited")
        assert typed.total == 1
        window = list_events(
            session,
            limit=50,
            offset=0,
            observed_from=datetime(2026, 9, 29, 17, 35, tzinfo=UTC),
            observed_until=datetime(2026, 9, 29, 17, 36, tzinfo=UTC),
        )
        assert window.total == 2
        with pytest.raises(PersistenceError) as limit:
            list_events(session, limit=101, offset=0)
        assert limit.value.code == "invalid_filter"
        with pytest.raises(PersistenceError) as kind:
            list_events(session, limit=10, offset=0, event_type="command_executed")
        assert kind.value.code == "invalid_filter"
        with pytest.raises(PersistenceError) as window_err:
            list_events(
                session,
                limit=10,
                offset=0,
                observed_from=datetime(2026, 9, 30, tzinfo=UTC),
                observed_until=datetime(2026, 9, 29, tzinfo=UTC),
            )
        assert window_err.value.code == "invalid_filter"
        assert get_event_by_id(session, uuid4()) is None
    finally:
        session.close()


def test_app_role_cannot_update_or_delete_evidence(tokens) -> None:
    session = _session(tokens)
    envelope, signature, key = _signed()
    try:
        persist_verified_event(session, envelope, signature, key.public_key())
        session.commit()
    finally:
        session.close()
    engine = create_engine(tokens["app_url"])
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("UPDATE telemetry_events SET identity_status = 'enrolled'"))
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM telemetry_events"))
    with engine.connect() as connection:
        status = connection.execute(
            text("SELECT identity_status, count(*) FROM telemetry_events GROUP BY 1")
        ).one()
        grants = (
            connection.execute(
                text(
                    """
                SELECT privilege_type FROM information_schema.role_table_grants
                WHERE table_name = 'telemetry_events' AND grantee = 'synapse_app'
                """
                )
            )
            .scalars()
            .all()
        )
    engine.dispose()
    assert status[0] == "unverified"
    assert set(grants) == {"SELECT", "INSERT"}


def test_database_unique_constraints_reject_direct_duplicates(tokens) -> None:
    session = _session(tokens)
    envelope, signature, key = _signed()
    try:
        persist_verified_event(session, envelope, signature, key.public_key())
        session.commit()
    finally:
        session.close()
    engine = create_engine(tokens["migration_url"])
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE telemetry_events DISABLE TRIGGER USER"))
            connection.execute(
                text(
                    """
                    INSERT INTO telemetry_events (
                        id, event_id, target_id, agent_id, boot_id, event_type, sequence,
                        observed_at, schema_version, envelope, signature, public_key_hex,
                        public_key_fingerprint, signature_verified, identity_status, received_at
                    )
                    SELECT gen_random_uuid(), event_id, target_id, agent_id, boot_id, event_type,
                           sequence + 1, observed_at, schema_version, envelope, signature,
                           public_key_hex, public_key_fingerprint, TRUE, 'unverified', received_at
                    FROM telemetry_events
                    """
                )
            )
    engine.dispose()


def test_persist_demo_uses_postgresql(tokens) -> None:
    from synapse_api.telemetry_persist_demo import main

    assert main([]) == 0


def test_migration_upgrade_and_downgrade_preserve_app_privileges(tokens) -> None:
    config = Config(str(ROOT / "apps" / "api" / "alembic.ini"))
    command.downgrade(config, "0002_enforce_state")
    engine = create_engine(tokens["migration_url"])
    try:
        inspector = inspect(engine)
        assert "telemetry_events" not in inspector.get_table_names()
        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert "telemetry_events" in inspector.get_table_names()
        with engine.connect() as connection:
            grants = (
                connection.execute(
                    text(
                        """
                    SELECT privilege_type FROM information_schema.role_table_grants
                    WHERE table_name = 'telemetry_events' AND grantee = 'synapse_app'
                    """
                    )
                )
                .scalars()
                .all()
            )
        assert "UPDATE" not in grants
        assert "DELETE" not in grants
        assert "INSERT" in grants
        assert "SELECT" in grants
    finally:
        engine.dispose()
        command.upgrade(config, "head")
