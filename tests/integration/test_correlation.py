"""PostgreSQL correlation persistence, idempotent findings, and HTTP access."""

from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from synapse_telemetry.normalization import normalize_observation
from synapse_telemetry.signatures import generate_signing_key, sign_event

from tests.integration.helpers import auth
from tests.integration.test_agent_enrollment import _create_target, _enroll
from tests.integration.test_telemetry_store import _raw

FIXED = "2026-09-29T17:34:00.000000Z"


def _ingest(client, envelope, signature):
    return client.post(
        "/api/v1/telemetry/ingest",
        json={"envelope": envelope.model_dump(mode="json"), "signature": signature},
    )


def _store_started(client, key, **extra):
    envelope = normalize_observation(_raw(observed_at=FIXED, **extra))
    signature = sign_event(key, envelope)
    response = _ingest(client, envelope, signature)
    assert response.status_code == 201, response.text
    return envelope


def test_normal_and_suspicious_correlation_via_api(client, tokens) -> None:
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    boot_id = str(uuid4())
    enrolled = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    assert enrolled.status_code == 201
    _store_started(
        client,
        key,
        target_id=target_id,
        agent_id=agent_id,
        boot_id=boot_id,
        sequence=1,
        pid=4242,
        start_ticks=11,
    )
    for index in range(6):
        envelope = normalize_observation(
            _raw(
                event_type="network_connection_observed",
                observed_at=f"2026-09-29T17:34:0{index + 1}.000000Z",
                target_id=target_id,
                agent_id=agent_id,
                boot_id=boot_id,
                sequence=index + 2,
                protocol="tcp",
                local_port=40000,
                remote_port=80 + index,
                remote_address="192.0.2.10",
                uid=1000,
                pid=4242,
            )
        )
        assert _ingest(client, envelope, sign_event(key, envelope)).status_code == 201
    run = client.post(
        f"/api/v1/targets/{target_id}/correlation/runs",
        headers=auth(tokens["admin"]),
        json={"window_seconds": 300},
    )
    assert run.status_code == 201, run.text
    body = run.json()
    assert body["risk"]["score"] > 0
    assert "min(100" in body["risk"]["formula"]
    forbidden = client.post(
        f"/api/v1/targets/{target_id}/correlation/runs",
        headers=auth(tokens["viewer"]),
        json={"window_seconds": 300},
    )
    assert forbidden.status_code == 403
    first_count = body["finding_count"]
    second = client.post(
        f"/api/v1/targets/{target_id}/correlation/runs",
        headers=auth(tokens["admin"]),
        json={"window_seconds": 300},
    )
    assert second.status_code == 201
    findings = client.get(
        f"/api/v1/targets/{target_id}/findings",
        headers=auth(tokens["viewer"]),
    )
    assert findings.status_code == 200
    page = findings.json()
    assert page["total"] == first_count
    item = page["items"][0]
    assert "signature" not in item
    assert "public_key" not in str(item).lower()
    detail = client.get(f"/api/v1/findings/{item['id']}", headers=auth(tokens["viewer"]))
    assert detail.status_code == 200
    assert detail.json()["supporting_event_ids"]
    assert detail.json()["epistemic_status"] in {"correlation", "inference"}
    links = client.get(
        f"/api/v1/targets/{target_id}/correlations",
        headers=auth(tokens["viewer"]),
    )
    assert links.status_code == 200
    assert links.json()["total"] >= 1
    risk = client.get(f"/api/v1/targets/{target_id}/risk", headers=auth(tokens["viewer"]))
    assert risk.status_code == 200
    assert risk.json()["score"] == body["risk"]["score"]


def test_app_role_cannot_delete_findings(client, tokens) -> None:
    inspector = inspect(create_engine(tokens["migration_url"]))
    assert inspector.has_table("findings")
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    envelope = normalize_observation(
        _raw(
            event_type="process_exited",
            observed_at=FIXED,
            target_id=target_id,
            agent_id=agent_id,
            boot_id=str(uuid4()),
            sequence=1,
            pid=9,
            start_ticks=1,
        )
    )
    assert _ingest(client, envelope, sign_event(key, envelope)).status_code == 201
    run = client.post(
        f"/api/v1/targets/{target_id}/correlation/runs",
        headers=auth(tokens["admin"]),
        json={"window_seconds": 60},
    )
    assert run.status_code == 201
    engine = create_engine(tokens["app_url"])
    with engine.connect() as connection:
        try:
            connection.execute(text("DELETE FROM findings"))
            connection.commit()
            raise AssertionError("delete should fail")
        except Exception as exc:
            message = str(exc).lower()
            assert "permission denied" in message or "cannot be deleted" in message
    engine.dispose()


def test_unauthenticated_correlation_reads_fail(client, tokens) -> None:
    target_id = _create_target(client, tokens)
    response = client.get(f"/api/v1/targets/{target_id}/findings")
    assert response.status_code == 401
