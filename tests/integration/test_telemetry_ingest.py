"""HTTP telemetry ingest: enrolled agents only, server-derived identity."""

import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Thread
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from synapse_api.ingest import ingest_telemetry
from synapse_api.telemetry_store import get_event_by_id, persist_verified_event
from synapse_contracts.telemetry_ingest import TelemetryIngestRequest
from synapse_telemetry.envelope import TelemetryEnvelope
from synapse_telemetry.signatures import generate_signing_key, sign_event

from tests.integration.helpers import auth
from tests.integration.test_agent_enrollment import _create_target, _enroll, _signed_with
from tests.integration.test_telemetry_store import _count, _session, _signed

INGEST = "/api/v1/telemetry/ingest"


def _body(envelope, signature: str) -> dict:
    return {"envelope": envelope.model_dump(mode="json"), "signature": signature}


def _event(key, event_type: str, **extra):
    payload = dict(extra)
    if event_type == "process_exited":
        payload.setdefault("pid", 4242)
        payload.setdefault("start_ticks", 123456)
        payload.pop("ppid", None)
        payload.pop("uid", None)
        payload.pop("comm", None)
    if event_type == "network_connection_observed":
        payload.setdefault("protocol", "tcp")
        payload.setdefault("local_port", 40000)
        payload.setdefault("remote_port", 443)
        payload.setdefault("remote_address", "192.0.2.10")
        payload.setdefault("uid", 1000)
        payload.setdefault("pid", 4242)
        payload.pop("ppid", None)
        payload.pop("comm", None)
        payload.pop("start_ticks", None)
    return _signed_with(key, event_type=event_type, **payload)


def _register(client, tokens, event_type: str = "process_started", **extra):
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    enrolled = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    assert enrolled.status_code == 201, enrolled.text
    envelope, signature = _event(
        key,
        event_type,
        target_id=target_id,
        agent_id=agent_id,
        **extra,
    )
    return target_id, agent_id, key, envelope, signature


@pytest.mark.parametrize(
    "event_type",
    ("process_started", "process_exited", "network_connection_observed"),
)
def test_enrolled_agent_can_ingest_each_event_type(client, tokens, event_type: str) -> None:
    _target_id, agent_id, key, envelope, signature = _register(client, tokens, event_type)
    response = client.post(INGEST, json=_body(envelope, signature))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["persistence_status"] == "stored"
    assert body["signature_verified"] is True
    assert body["identity_status"] == "enrolled"
    assert body["event_id"] == str(envelope.event_id)
    assert body["agent_id"] == agent_id
    assert body["event_type"] == event_type
    assert "signature" not in body
    assert "public_key_hex" not in body
    assert "envelope" not in body
    session = _session(tokens)
    try:
        stored = get_event_by_id(session, envelope.event_id)
        assert stored is not None
        assert stored.identity_status == "enrolled"
        assert stored.signature_verified is True
        assert stored.public_key_hex == key.public_key().raw_bytes().hex()
    finally:
        session.close()


def test_unknown_agent_is_rejected_by_http_and_does_not_store(client, tokens) -> None:
    envelope, signature, _key = _signed()
    before = _count(tokens)
    response = client.post(INGEST, json=_body(envelope, signature))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "unknown_agent"
    assert _count(tokens) == before
    session = _session(tokens)
    try:
        persist_verified_event(session, envelope, signature, _key.public_key())
        session.commit()
        stored = get_event_by_id(session, envelope.event_id)
        assert stored is not None
        assert stored.identity_status == "unverified"
    finally:
        session.close()


def test_revoked_agent_and_inactive_target_are_rejected(client, tokens) -> None:
    target_id, agent_id, key, envelope, signature = _register(client, tokens)
    revoked = client.post(
        f"/api/v1/agents/{agent_id}/revocation",
        headers=auth(tokens["admin"]),
    )
    assert revoked.status_code == 200
    refused = client.post(INGEST, json=_body(envelope, signature))
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "revoked_agent"

    target_b = _create_target(client, tokens)
    key_b = generate_signing_key()
    agent_b = str(uuid4())
    enrolled = _enroll(client, tokens, target_b, key_b.public_key().raw_bytes().hex(), agent_b)
    assert enrolled.status_code == 201
    client.post(f"/api/v1/targets/{target_b}/revocation", headers=auth(tokens["admin"]))
    env_b, sig_b = _signed_with(key_b, target_id=target_b, agent_id=agent_b, sequence=1)
    inactive = client.post(INGEST, json=_body(env_b, sig_b))
    assert inactive.status_code == 409
    assert inactive.json()["error"]["code"] == "inactive_target"
    assert _count(tokens) == 0


def test_target_mismatch_and_rotated_key_are_rejected(client, tokens) -> None:
    target_id, agent_id, key, envelope, signature = _register(client, tokens)
    other_target = _create_target(client, tokens)
    mismatched, mismatched_sig = _signed_with(
        key, target_id=other_target, agent_id=agent_id, sequence=1
    )
    mismatch = client.post(INGEST, json=_body(mismatched, mismatched_sig))
    assert mismatch.status_code == 403
    assert mismatch.json()["error"]["code"] == "target_mismatch"

    new_key = generate_signing_key()
    rotated = client.post(
        f"/api/v1/agents/{agent_id}/rotation",
        headers=auth(tokens["admin"]),
        json={"public_key_hex": new_key.public_key().raw_bytes().hex()},
    )
    assert rotated.status_code == 200
    stale = client.post(INGEST, json=_body(envelope, signature))
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "invalid_signature"
    fresh, fresh_sig = _signed_with(new_key, target_id=target_id, agent_id=agent_id, sequence=1)
    accepted = client.post(INGEST, json=_body(fresh, fresh_sig))
    assert accepted.status_code == 201


def test_caller_supplied_trust_labels_and_viewer_admin_ops_are_rejected(client, tokens) -> None:
    _target_id, _agent_id, _key, envelope, signature = _register(client, tokens)
    payload = _body(envelope, signature)
    payload["verified"] = True
    payload["identity_status"] = "authorized"
    rejected = client.post(INGEST, json=payload)
    assert rejected.status_code == 422
    denied = client.post(
        f"/api/v1/targets/{_target_id}/agents",
        headers=auth(tokens["viewer"]),
        json={"public_key_hex": generate_signing_key().public_key().raw_bytes().hex()},
    )
    assert denied.status_code == 403


def test_integrity_failures_do_not_create_rows(client, tokens) -> None:
    target_id, agent_id, key, envelope, signature = _register(client, tokens)
    before = _count(tokens)

    tampered = envelope.model_dump(mode="json")
    tampered["payload"]["comm"] = "sshd"
    tampered_sig = sign_event(key, envelope)
    bad_payload = client.post(INGEST, json={"envelope": tampered, "signature": tampered_sig})
    assert bad_payload.status_code == 401

    other_target = str(uuid4())
    target_doc = envelope.model_dump(mode="json")
    target_doc["target_id"] = other_target
    bad_target = client.post(INGEST, json={"envelope": target_doc, "signature": signature})
    assert bad_target.status_code in {401, 422}

    agent_doc = envelope.model_dump(mode="json")
    agent_doc["agent_id"] = str(uuid4())
    bad_agent = client.post(INGEST, json={"envelope": agent_doc, "signature": signature})
    assert bad_agent.status_code in {401, 403, 422}

    truncated = client.post(
        INGEST,
        json={"envelope": envelope.model_dump(mode="json"), "signature": "AAAA"},
    )
    assert truncated.status_code == 422

    invalid_b64 = client.post(
        INGEST,
        json={"envelope": envelope.model_dump(mode="json"), "signature": "!" * 86 + "=="},
    )
    assert invalid_b64.status_code == 422

    other = generate_signing_key()
    wrong_sig = sign_event(other, envelope)
    wrong_key = client.post(INGEST, json=_body(envelope, wrong_sig))
    assert wrong_key.status_code == 401

    schema = envelope.model_dump(mode="json")
    schema["event_type"] = "command_executed"
    invalid_schema = client.post(INGEST, json={"envelope": schema, "signature": signature})
    assert invalid_schema.status_code == 422
    assert _count(tokens) == before
    assert target_id
    assert agent_id


def test_exact_duplicate_is_idempotent_and_conflicts_do_not_overwrite(client, tokens) -> None:
    _target_id, _agent_id, key, envelope, signature = _register(client, tokens)
    first = client.post(INGEST, json=_body(envelope, signature))
    assert first.status_code == 201
    event_id = first.json()["event_id"]
    duplicate = client.post(INGEST, json=_body(envelope, signature))
    assert duplicate.status_code == 200
    assert duplicate.json()["persistence_status"] == "duplicate"
    assert duplicate.json()["event_id"] == event_id

    changed = envelope.model_dump(mode="json")
    changed["payload"]["pid"] = 99
    changed_model = TelemetryEnvelope.model_validate(changed)
    changed_sig = sign_event(key, changed_model)
    conflict = client.post(INGEST, json=_body(changed_model, changed_sig))
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "event_id_conflict"

    replay = envelope.model_dump(mode="json")
    replay["event_id"] = str(uuid4())
    replay_model = TelemetryEnvelope.model_validate(replay)
    replay_sig = sign_event(key, replay_model)
    sequence = client.post(INGEST, json=_body(replay_model, replay_sig))
    assert sequence.status_code == 409
    assert sequence.json()["error"]["code"] == "sequence_conflict"
    assert _count(tokens) == 1
    session = _session(tokens)
    try:
        stored = get_event_by_id(session, envelope.event_id)
        assert stored is not None
        assert stored.envelope["payload"]["pid"] == 4242
    finally:
        session.close()


def test_concurrent_duplicate_ingest_creates_one_row(client, tokens) -> None:
    _target_id, _agent_id, _key, envelope, signature = _register(client, tokens)
    request = TelemetryIngestRequest(envelope=envelope, signature=signature)
    barrier = Barrier(2)
    outcomes: list[int] = []

    def worker() -> None:
        session = _session(tokens)
        try:
            barrier.wait(timeout=5)
            result = ingest_telemetry(session, request)
            session.commit()
            outcomes.append(result.status_code)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker), pool.submit(worker)]
        for future in futures:
            future.result(timeout=15)
    assert sorted(outcomes) == [200, 201]
    assert _count(tokens) == 1


def test_revocation_racing_ingest_is_fail_closed(client, tokens) -> None:
    target_id, agent_id, key, envelope, signature = _register(client, tokens)
    request = TelemetryIngestRequest(envelope=envelope, signature=signature)
    application = create_engine(tokens["app_url"])
    holder = application.connect()
    transaction = holder.begin()
    outcome: list[int] = []

    def worker() -> None:
        session = Session(application)
        session.execute(text("SET lock_timeout = '15s'"))
        try:
            result = ingest_telemetry(session, request)
            session.commit()
            outcome.append(result.status_code)
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
            while time.monotonic() < deadline:
                waiting = watch.execute(
                    text(
                        """
                        SELECT count(*) FROM pg_locks
                        WHERE NOT granted AND locktype = 'transactionid'
                        """
                    )
                ).scalar()
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
    assert outcome == [403]
    assert _count(tokens) == 0
    assert target_id
    assert key


def test_key_rotation_racing_ingest_rejects_stale_signature(client, tokens) -> None:
    target_id, agent_id, key, envelope, signature = _register(client, tokens)
    request = TelemetryIngestRequest(envelope=envelope, signature=signature)
    new_key = generate_signing_key()
    application = create_engine(tokens["app_url"])
    holder = application.connect()
    transaction = holder.begin()
    outcome: list[int] = []

    def worker() -> None:
        session = Session(application)
        session.execute(text("SET lock_timeout = '15s'"))
        try:
            result = ingest_telemetry(session, request)
            session.commit()
            outcome.append(result.status_code)
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
            while time.monotonic() < deadline:
                waiting = watch.execute(
                    text(
                        """
                        SELECT count(*) FROM pg_locks
                        WHERE NOT granted AND locktype = 'transactionid'
                        """
                    )
                ).scalar()
                if waiting:
                    break
                time.sleep(0.05)
        owner.dispose()
        holder.execute(
            text(
                """
                UPDATE agents
                SET public_key_hex = :hex,
                    public_key_fingerprint = :fp,
                    key_generation = key_generation + 1,
                    updated_at = NOW()
                WHERE id = :agent_id
                """
            ),
            {
                "agent_id": agent_id,
                "hex": new_key.public_key().raw_bytes().hex(),
                "fp": f"sha256:{'ab' * 32}",
            },
        )
        transaction.commit()
        thread.join(timeout=15)
    finally:
        if transaction.is_active:
            transaction.rollback()
        holder.close()
        application.dispose()
    assert outcome == [401]
    assert _count(tokens) == 0
    assert UUID(target_id)


def test_http_robustness(client, tokens) -> None:
    malformed = client.post(
        INGEST,
        content=b"{",
        headers={"content-type": "application/json"},
    )
    assert malformed.status_code == 422
    missing = client.post(INGEST, json={})
    assert missing.status_code == 422
    extra = client.post(
        INGEST,
        json={"envelope": {}, "signature": "A" * 86 + "==", "trusted": True},
    )
    assert extra.status_code == 422
    oversized = client.post(
        INGEST,
        content=b"{" + b"a" * 70000 + b"}",
        headers={"content-type": "application/json"},
    )
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "payload_too_large"
    plain = client.post(
        INGEST,
        content=b"{}",
        headers={"content-type": "text/plain"},
    )
    assert plain.status_code == 415
    invalid_id = client.post(
        INGEST,
        json={
            "envelope": {"event_type": "process_started", "agent_id": "not-a-uuid"},
            "signature": "A" * 86 + "==",
        },
    )
    assert invalid_id.status_code == 422


def test_unexpected_ingest_error_does_not_leak_details(client, tokens, monkeypatch) -> None:
    from synapse_api import ingest as ingest_module

    target_id, agent_id, key, envelope, signature = _register(client, tokens)

    def boom(*_args, **_kwargs):
        raise RuntimeError("postgresql+psycopg://synapse_app:super-secret-db@postgres/synapse")

    monkeypatch.setattr(ingest_module, "persist_verified_event", boom)
    from fastapi.testclient import TestClient

    with TestClient(client.app, raise_server_exceptions=False) as leak_client:
        response = leak_client.post(INGEST, json=_body(envelope, signature))
    assert response.status_code == 500
    text_body = response.text.lower()
    assert "super-secret-db" not in text_body
    assert "postgresql" not in text_body
    assert response.json()["error"]["code"] == "internal_error"
    assert target_id
    assert agent_id
    assert key


def test_audit_records_ingest_without_payloads(client, tokens) -> None:
    _target_id, _agent_id, _key, envelope, signature = _register(client, tokens)
    assert client.post(INGEST, json=_body(envelope, signature)).status_code == 201
    events = client.get("/api/v1/audit/events", headers=auth(tokens["viewer"]))
    ingested = [
        item for item in events.json()["items"] if item["event_type"] == "telemetry.ingested"
    ]
    assert ingested
    payload = ingested[0]["payload"]
    assert "signature" not in payload
    assert "envelope" not in payload
    assert "comm" not in str(payload)
    assert payload["event_id"] == str(envelope.event_id)
