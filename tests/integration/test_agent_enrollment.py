"""Administrator enrollment, identity verification, and evidence binding."""

import time
from concurrent.futures import ThreadPoolExecutor
from inspect import signature
from threading import Barrier, Thread
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from synapse_api.enrollment import enroll_agent, evaluate_identity
from synapse_api.errors import ApiError
from synapse_api.telemetry_store import PersistenceError, get_event_by_id, persist_verified_event
from synapse_contracts.agents import AgentEnroll
from synapse_telemetry.normalization import normalize_observation
from synapse_telemetry.signatures import generate_signing_key, sign_event

from tests.integration.conftest import ROOT
from tests.integration.helpers import auth, target_payload
from tests.integration.test_telemetry_store import _raw, _session

FIXED_TIME = "2026-09-29T17:34:00.000000Z"


def _create_target(client, tokens, **overrides) -> str:
    created = client.post(
        "/api/v1/targets",
        headers=auth(tokens["admin"]),
        json=target_payload(**overrides),
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _enroll(client, tokens, target_id: str, public_key_hex: str, agent_id: str | None = None):
    body: dict[str, object] = {"public_key_hex": public_key_hex}
    if agent_id is not None:
        body["agent_id"] = agent_id
    return client.post(
        f"/api/v1/targets/{target_id}/agents",
        headers=auth(tokens["admin"]),
        json=body,
    )


def _signed_with(key, **extra):
    envelope = normalize_observation(_raw(observed_at=FIXED_TIME, **extra))
    signature = sign_event(key, envelope)
    return envelope, signature


def test_administrator_enrolls_an_agent(client, tokens) -> None:
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    created = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["id"] == agent_id
    assert body["target_id"] == target_id
    assert body["status"] == "active"
    assert body["key_generation"] == 1
    assert body["public_key_hex"] == key.public_key().raw_bytes().hex()
    assert body["public_key_fingerprint"].startswith("sha256:")
    assert body["revoked_at"] is None
    listed = client.get(
        f"/api/v1/targets/{target_id}/agents",
        headers=auth(tokens["viewer"]),
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    fetched = client.get(f"/api/v1/agents/{agent_id}", headers=auth(tokens["viewer"]))
    assert fetched.status_code == 200
    events = client.get("/api/v1/audit/events", headers=auth(tokens["viewer"]))
    types = {item["event_type"] for item in events.json()["items"]}
    assert "agent.enrolled" in types
    payload = next(
        item["payload"] for item in events.json()["items"] if item["event_type"] == "agent.enrolled"
    )
    assert "private" not in str(payload).lower()
    assert payload["public_key_fingerprint"] == body["public_key_fingerprint"]


def test_viewer_cannot_enroll_or_revoke_or_rotate(client, tokens) -> None:
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    denied = client.post(
        f"/api/v1/targets/{target_id}/agents",
        headers=auth(tokens["viewer"]),
        json={"public_key_hex": key.public_key().raw_bytes().hex()},
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "authorization_failed"
    enrolled = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex())
    agent_id = enrolled.json()["id"]
    rotate = client.post(
        f"/api/v1/agents/{agent_id}/rotation",
        headers=auth(tokens["viewer"]),
        json={"public_key_hex": generate_signing_key().public_key().raw_bytes().hex()},
    )
    assert rotate.status_code == 403
    revoke = client.post(
        f"/api/v1/agents/{agent_id}/revocation",
        headers=auth(tokens["viewer"]),
    )
    assert revoke.status_code == 403


def test_invalid_and_duplicate_enrollment_are_rejected(client, tokens) -> None:
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    invalid = _enroll(client, tokens, target_id, "zz" * 32)
    assert invalid.status_code == 422
    missing = client.post(
        f"/api/v1/targets/{target_id}/agents",
        headers=auth(tokens["admin"]),
        json={},
    )
    assert missing.status_code == 422
    secret = client.post(
        f"/api/v1/targets/{target_id}/agents",
        headers=auth(tokens["admin"]),
        json={
            "public_key_hex": key.public_key().raw_bytes().hex(),
            "private_key_hex": "00" * 32,
        },
    )
    assert secret.status_code == 422
    unknown_target = _enroll(client, tokens, str(uuid4()), key.public_key().raw_bytes().hex())
    assert unknown_target.status_code == 404
    first = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex())
    assert first.status_code == 201
    duplicate_key = _enroll(
        client, tokens, target_id, key.public_key().raw_bytes().hex(), str(uuid4())
    )
    assert duplicate_key.status_code == 409
    assert duplicate_key.json()["error"]["code"] == "public_key_already_registered"
    duplicate_id = _enroll(
        client,
        tokens,
        target_id,
        generate_signing_key().public_key().raw_bytes().hex(),
        first.json()["id"],
    )
    assert duplicate_id.status_code == 409
    assert duplicate_id.json()["error"]["code"] == "agent_already_enrolled"


def test_unauthorized_and_revoked_targets_cannot_enroll(client, tokens) -> None:
    key = generate_signing_key()
    weak = _create_target(client, tokens, allowed_capabilities=["evidence.submit"])
    denied = _enroll(client, tokens, weak, key.public_key().raw_bytes().hex())
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "target_not_eligible"
    target_id = _create_target(client, tokens)
    revoked = client.post(
        f"/api/v1/targets/{target_id}/revocation",
        headers=auth(tokens["admin"]),
    )
    assert revoked.status_code == 200
    rejected = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex())
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "target_not_eligible"


def test_agents_table_does_not_store_private_keys(client, tokens) -> None:
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    created = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex())
    assert created.status_code == 201
    engine = create_engine(tokens["migration_url"])
    try:
        names = {column["name"] for column in inspect(engine).get_columns("agents")}
        with engine.connect() as connection:
            row = connection.execute(text("SELECT * FROM agents")).mappings().one()
    finally:
        engine.dispose()
    assert all("private" not in name for name in names)
    dumped = " ".join(f"{key_name}={value}" for key_name, value in row.items())
    assert "private" not in dumped.lower()
    assert str(key) == "SigningKey(redacted)"


def test_identity_outcomes(client, tokens) -> None:
    session = _session(tokens)
    key = generate_signing_key()
    other = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    created = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    assert created.status_code == 201
    other_target = _create_target(client, tokens)
    try:
        unknown = evaluate_identity(session, uuid4(), uuid4(), key.public_key())
        assert unknown.status == "unknown_agent"
        matched = evaluate_identity(session, UUID(agent_id), UUID(target_id), key.public_key())
        assert matched.status == "enrolled"
        wrong_key = evaluate_identity(session, UUID(agent_id), UUID(target_id), other.public_key())
        assert wrong_key.status == "key_mismatch"
        wrong_target = evaluate_identity(
            session, UUID(agent_id), UUID(other_target), key.public_key()
        )
        assert wrong_target.status == "target_mismatch"
        session.rollback()
        revoked = client.post(
            f"/api/v1/agents/{agent_id}/revocation",
            headers=auth(tokens["admin"]),
        )
        assert revoked.status_code == 200
        session.expire_all()
        gone = evaluate_identity(session, UUID(agent_id), UUID(target_id), key.public_key())
        assert gone.status == "revoked_agent"
        second_key = generate_signing_key()
        second_id = str(uuid4())
        second = _enroll(
            client, tokens, other_target, second_key.public_key().raw_bytes().hex(), second_id
        )
        assert second.status_code == 201
        client.post(
            f"/api/v1/targets/{other_target}/revocation",
            headers=auth(tokens["admin"]),
        )
        session.expire_all()
        inactive = evaluate_identity(
            session, UUID(second_id), UUID(other_target), second_key.public_key()
        )
        assert inactive.status == "inactive_target"
    finally:
        session.close()


def test_persist_derives_identity_and_rejects_caller_labels(client, tokens) -> None:
    assert "identity_status" not in signature(persist_verified_event).parameters
    session = _session(tokens)
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    created = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    assert created.status_code == 201
    try:
        envelope, signature_value = _signed_with(
            key, target_id=target_id, agent_id=agent_id, sequence=1
        )
        stored = persist_verified_event(session, envelope, signature_value, key.public_key())
        session.commit()
        assert stored.record.signature_verified is True
        assert stored.record.identity_status == "enrolled"
        unsigned_key = generate_signing_key()
        unverified_env, unverified_sig = _signed_with(unsigned_key, sequence=1)
        unverified = persist_verified_event(
            session, unverified_env, unverified_sig, unsigned_key.public_key()
        )
        session.commit()
        assert unverified.record.identity_status == "unverified"
        assert get_event_by_id(session, unverified_env.event_id) is not None
        with pytest.raises(TypeError):
            persist_verified_event(
                session,
                unverified_env,
                unverified_sig,
                unsigned_key.public_key(),
                identity_status="enrolled",
            )
        other = generate_signing_key()
        mismatch_env, mismatch_sig = _signed_with(
            other, target_id=target_id, agent_id=agent_id, sequence=2
        )
        with pytest.raises(PersistenceError) as key_err:
            persist_verified_event(session, mismatch_env, mismatch_sig, other.public_key())
        assert key_err.value.code == "key_mismatch"
        wrong_target = str(uuid4())
        target_env, target_sig = _signed_with(
            key, target_id=wrong_target, agent_id=agent_id, sequence=3
        )
        with pytest.raises(PersistenceError) as target_err:
            persist_verified_event(session, target_env, target_sig, key.public_key())
        assert target_err.value.code == "target_mismatch"
        session.rollback()
    finally:
        session.close()


def test_revoked_agent_cannot_store_new_evidence(client, tokens) -> None:
    session = _session(tokens)
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    created = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    assert created.status_code == 201
    try:
        first, first_sig = _signed_with(key, target_id=target_id, agent_id=agent_id, sequence=1)
        persist_verified_event(session, first, first_sig, key.public_key())
        session.commit()
        revoked = client.post(
            f"/api/v1/agents/{agent_id}/revocation",
            headers=auth(tokens["admin"]),
        )
        assert revoked.status_code == 200
        again = client.post(
            f"/api/v1/agents/{agent_id}/revocation",
            headers=auth(tokens["admin"]),
        )
        assert again.status_code == 409
        second, second_sig = _signed_with(key, target_id=target_id, agent_id=agent_id, sequence=2)
        with pytest.raises(PersistenceError) as refused:
            persist_verified_event(session, second, second_sig, key.public_key())
        assert refused.value.code == "revoked_agent"
        session.rollback()
        historical = get_event_by_id(session, first.event_id)
        assert historical is not None
        assert historical.identity_status == "enrolled"
        assert historical.public_key_hex == key.public_key().raw_bytes().hex()
    finally:
        session.close()


def test_key_rotation_preserves_historical_evidence(client, tokens) -> None:
    session = _session(tokens)
    old_key = generate_signing_key()
    new_key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    created = _enroll(client, tokens, target_id, old_key.public_key().raw_bytes().hex(), agent_id)
    assert created.status_code == 201
    try:
        first, first_sig = _signed_with(old_key, target_id=target_id, agent_id=agent_id, sequence=1)
        persist_verified_event(session, first, first_sig, old_key.public_key())
        session.commit()
        rotated = client.post(
            f"/api/v1/agents/{agent_id}/rotation",
            headers=auth(tokens["admin"]),
            json={"public_key_hex": new_key.public_key().raw_bytes().hex()},
        )
        assert rotated.status_code == 200, rotated.text
        assert rotated.json()["key_generation"] == 2
        stale, stale_sig = _signed_with(old_key, target_id=target_id, agent_id=agent_id, sequence=2)
        with pytest.raises(PersistenceError) as stale_err:
            persist_verified_event(session, stale, stale_sig, old_key.public_key())
        assert stale_err.value.code == "key_mismatch"
        session.rollback()
        fresh, fresh_sig = _signed_with(new_key, target_id=target_id, agent_id=agent_id, sequence=2)
        stored = persist_verified_event(session, fresh, fresh_sig, new_key.public_key())
        session.commit()
        assert stored.record.identity_status == "enrolled"
        historical = get_event_by_id(session, first.event_id)
        assert historical is not None
        assert historical.public_key_hex == old_key.public_key().raw_bytes().hex()
        assert historical.public_key_hex != new_key.public_key().raw_bytes().hex()
    finally:
        session.close()


def test_inactive_target_rejects_new_enrolled_evidence(client, tokens) -> None:
    session = _session(tokens)
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    created = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    assert created.status_code == 201
    client.post(f"/api/v1/targets/{target_id}/revocation", headers=auth(tokens["admin"]))
    try:
        envelope, signature_value = _signed_with(
            key, target_id=target_id, agent_id=agent_id, sequence=1
        )
        with pytest.raises(PersistenceError) as refused:
            persist_verified_event(session, envelope, signature_value, key.public_key())
        assert refused.value.code == "inactive_target"
        session.rollback()
    finally:
        session.close()


def test_persist_rolls_back_when_identity_is_rejected(client, tokens) -> None:
    session = _session(tokens)
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    created = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    assert created.status_code == 201
    other = generate_signing_key()
    try:
        envelope, signature_value = _signed_with(
            other, target_id=target_id, agent_id=agent_id, sequence=1
        )
        with pytest.raises(PersistenceError):
            persist_verified_event(session, envelope, signature_value, other.public_key())
        session.rollback()
        engine = create_engine(tokens["app_url"])
        with engine.connect() as connection:
            count = connection.execute(text("SELECT count(*) FROM telemetry_events")).scalar()
        engine.dispose()
        assert count == 0
    finally:
        session.close()


def test_concurrent_enrollment_of_the_same_agent(client, tokens) -> None:
    target_id = UUID(_create_target(client, tokens))
    agent_id = uuid4()
    barrier = Barrier(2)
    outcomes: list[str] = []

    def worker(hex_key: str) -> None:
        session = _session(tokens)
        try:
            barrier.wait(timeout=5)
            enroll_agent(
                session,
                target_id,
                AgentEnroll(public_key_hex=hex_key, agent_id=agent_id),
                "test-admin",
            )
            session.commit()
            outcomes.append("created")
        except ApiError as exc:
            session.rollback()
            outcomes.append(exc.code)
        except Exception as exc:
            session.rollback()
            outcomes.append(type(exc).__name__)
        finally:
            session.close()

    keys = [generate_signing_key(), generate_signing_key()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(worker, keys[0].public_key().raw_bytes().hex()),
            pool.submit(worker, keys[1].public_key().raw_bytes().hex()),
        ]
        for future in futures:
            future.result(timeout=15)
    assert sorted(outcomes) == ["agent_already_enrolled", "created"]
    listed = client.get(
        f"/api/v1/targets/{target_id}/agents",
        headers=auth(tokens["admin"]),
    )
    assert listed.json()["total"] == 1


def test_revocation_blocks_persist_waiting_on_the_agent_lock(client, tokens) -> None:
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    created = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    assert created.status_code == 201
    application = create_engine(tokens["app_url"])
    holder = application.connect()
    transaction = holder.begin()
    outcome: list[str] = []
    envelope, signature_value = _signed_with(
        key, target_id=target_id, agent_id=agent_id, sequence=1
    )

    def worker() -> None:
        session = Session(application)
        session.execute(text("SET lock_timeout = '15s'"))
        try:
            persist_verified_event(session, envelope, signature_value, key.public_key())
            session.commit()
            outcome.append("stored")
        except PersistenceError as exc:
            session.rollback()
            outcome.append(exc.code)
        except Exception as exc:
            session.rollback()
            outcome.append(type(exc).__name__)
        finally:
            session.close()

    try:
        holder.execute(
            text("SELECT id FROM agents WHERE id = :agent_id FOR UPDATE"),
            {"agent_id": agent_id},
        )
        thread = Thread(target=worker)
        thread.start()
        deadline = time.monotonic() + 5
        owner = create_engine(tokens["migration_url"])
        with owner.connect() as watch:
            waiting = False
            while time.monotonic() < deadline:
                waiting = bool(
                    watch.execute(
                        text(
                            """
                            SELECT count(*) FROM pg_locks
                            WHERE NOT granted AND locktype = 'transactionid'
                            """
                        )
                    ).scalar()
                )
                if waiting:
                    break
                time.sleep(0.05)
        owner.dispose()
        holder.execute(
            text(
                "UPDATE agents SET status = 'revoked', revoked_at = NOW(), updated_at = NOW() "
                "WHERE id = :agent_id"
            ),
            {"agent_id": agent_id},
        )
        transaction.commit()
        thread.join(timeout=15)
    finally:
        if transaction.is_active:
            transaction.rollback()
        holder.close()
        application.dispose()
    assert outcome == ["revoked_agent"]


def test_app_role_cannot_bypass_agent_or_evidence_protections(client, tokens) -> None:
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    created = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex())
    agent_id = created.json()["id"]
    application = create_engine(tokens["app_url"])
    with pytest.raises(DBAPIError):
        with application.begin() as connection:
            connection.execute(
                text("UPDATE agents SET enrolled_by = 'intruder' WHERE id = :agent_id"),
                {"agent_id": agent_id},
            )
    with pytest.raises(DBAPIError):
        with application.begin() as connection:
            connection.execute(
                text("UPDATE agents SET target_id = :target_id WHERE id = :agent_id"),
                {"agent_id": agent_id, "target_id": str(uuid4())},
            )
    with pytest.raises(DBAPIError):
        with application.begin() as connection:
            connection.execute(text("DELETE FROM agents"))
    with application.begin() as connection:
        connection.execute(
            text(
                "UPDATE agents SET status = 'revoked', revoked_at = NOW(), updated_at = NOW() "
                "WHERE id = :agent_id"
            ),
            {"agent_id": agent_id},
        )
    with pytest.raises(DBAPIError):
        with application.begin() as connection:
            connection.execute(
                text(
                    "UPDATE agents SET status = 'active', revoked_at = NULL, updated_at = NOW() "
                    "WHERE id = :agent_id"
                ),
                {"agent_id": agent_id},
            )
    with pytest.raises(DBAPIError):
        with application.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO telemetry_events (
                        id, event_id, target_id, agent_id, boot_id, event_type, sequence,
                        observed_at, schema_version, envelope, signature, public_key_hex,
                        public_key_fingerprint, signature_verified, identity_status, received_at
                    )
                    VALUES (
                        gen_random_uuid(), gen_random_uuid(), :target_id, gen_random_uuid(),
                        gen_random_uuid(), 'process_started', 1, NOW(), '1.0.0',
                        '{"schema_version":"1.0.0"}'::jsonb,
                        :signature, :public_key, :fingerprint, TRUE, 'enrolled', NOW()
                    )
                    """
                ),
                {
                    "target_id": target_id,
                    "signature": "A" * 86 + "==",
                    "public_key": key.public_key().raw_bytes().hex(),
                    "fingerprint": created.json()["public_key_fingerprint"],
                },
            )
    with application.connect() as connection:
        grants = (
            connection.execute(
                text(
                    """
                    SELECT privilege_type FROM information_schema.column_privileges
                    WHERE table_name = 'agents' AND grantee = 'synapse_app'
                      AND column_name = 'enrolled_by'
                    """
                )
            )
            .scalars()
            .all()
        )
        evidence_grants = (
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
    application.dispose()
    assert "UPDATE" not in grants
    assert set(evidence_grants) == {"SELECT", "INSERT"}


def test_migration_upgrade_and_downgrade_agents(tokens) -> None:
    config = Config(str(ROOT / "apps" / "api" / "alembic.ini"))
    engine = create_engine(tokens["migration_url"])
    try:
        command.downgrade(config, "0003_telemetry_events")
        inspector = inspect(engine)
        assert "agents" not in inspector.get_table_names()
        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert "agents" in inspector.get_table_names()
        with engine.connect() as connection:
            grants = (
                connection.execute(
                    text(
                        """
                        SELECT privilege_type FROM information_schema.role_table_grants
                        WHERE table_name = 'agents' AND grantee = 'synapse_app'
                        """
                    )
                )
                .scalars()
                .all()
            )
            owner = connection.execute(
                text(
                    """
                    SELECT pg_get_userbyid(relowner)
                    FROM pg_class
                    WHERE relname = 'agents'
                    """
                )
            ).scalar()
        assert "DELETE" not in grants
        assert "INSERT" in grants
        assert "SELECT" in grants
        assert owner != "synapse_app"
    finally:
        engine.dispose()
        command.upgrade(config, "head")
