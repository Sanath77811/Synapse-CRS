"""API tests for authorization, cases, audit, and authentication."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.integration.helpers import auth, target_payload

PIPELINE = [
    "OBSERVATION",
    "EVIDENCE",
    "HYPOTHESIS",
    "VERIFICATION",
    "APPROVAL",
    "ACTION",
    "VALIDATION",
    "ROLLBACK",
    "SEALED_AUDIT",
]


def test_health_and_ready_do_not_require_a_token(client) -> None:
    health = client.get("/health")
    ready = client.get("/ready")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json()["database"] == "ok"
    assert "password" not in ready.text.lower()


def test_missing_and_rejected_tokens_fail_closed(client) -> None:
    missing = client.get("/api/v1/targets")
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"

    rejected = client.get("/api/v1/targets", headers=auth("not-a-valid-token-value"))
    assert rejected.status_code == 401
    assert rejected.json()["error"]["code"] == "authentication_failed"
    assert "not-a-valid-token-value" not in rejected.text


def test_viewer_cannot_create_or_revoke_targets(client, tokens) -> None:
    created = client.post(
        "/api/v1/targets",
        headers=auth(tokens["viewer"]),
        json=target_payload(),
    )
    assert created.status_code == 403
    assert created.json()["error"]["code"] == "authorization_failed"

    admin_created = client.post(
        "/api/v1/targets",
        headers=auth(tokens["admin"]),
        json=target_payload(),
    )
    assert admin_created.status_code == 201
    target_id = admin_created.json()["id"]
    revoked = client.post(
        f"/api/v1/targets/{target_id}/revocation",
        headers=auth(tokens["viewer"]),
    )
    assert revoked.status_code == 403


def test_target_creation_records_eligibility_and_audit(client, tokens) -> None:
    response = client.post(
        "/api/v1/targets",
        headers=auth(tokens["admin"]),
        json=target_payload(name="lab-edge"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["eligible"] is True
    assert body["authorization_status"] == "active"
    assert body["eligibility_reasons"] == []
    assert body["owner"] == "research-team"
    assert body["created_at"]
    assert body["updated_at"]

    listed = client.get("/api/v1/targets", headers=auth(tokens["viewer"]))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    eligibility = client.get(
        f"/api/v1/targets/{body['id']}/eligibility",
        headers=auth(tokens["viewer"]),
    )
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is True

    audit = client.get("/api/v1/audit/events", headers=auth(tokens["viewer"]))
    assert audit.status_code == 200
    event = audit.json()["items"][0]
    assert event["event_type"] == "target.created"
    assert event["actor"] == "test-admin"
    assert event["target_id"] == body["id"]
    assert tokens["admin"] not in audit.text
    assert event["previous_event_hash"] == "0" * 64
    assert len(event["event_hash"]) == 64


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (
            target_payload(authorization_expiry="2020-01-01T00:00:00Z"),
            "authorization_expiry_not_in_future",
        ),
        (target_payload(allowed_capabilities=["shell.execute"]), "invalid_request"),
        (target_payload(allowed_capabilities=[]), "invalid_request"),
        (
            target_payload(
                scope={
                    "environment": "production",
                    "assets": ["lab-app-1.internal"],
                    "description": "Owned laboratory application fixture.",
                }
            ),
            "invalid_request",
        ),
        (
            target_payload(
                scope={
                    "environment": "lab",
                    "assets": ["*"],
                    "description": "Owned laboratory application fixture.",
                }
            ),
            "invalid_request",
        ),
        (
            target_payload(
                scope={
                    "environment": "lab",
                    "assets": [],
                    "description": "Owned laboratory application fixture.",
                }
            ),
            "invalid_request",
        ),
    ],
)
def test_invalid_authorization_is_rejected(client, tokens, payload: dict, code: str) -> None:
    response = client.post("/api/v1/targets", headers=auth(tokens["admin"]), json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_spoofed_actor_field_is_rejected(client, tokens) -> None:
    payload = target_payload()
    payload["actor"] = "someone-else"
    response = client.post("/api/v1/targets", headers=auth(tokens["admin"]), json=payload)
    assert response.status_code == 422


def test_expired_and_revoked_targets_cannot_open_or_advance_cases(client, tokens) -> None:
    created = client.post(
        "/api/v1/targets",
        headers=auth(tokens["admin"]),
        json=target_payload(),
    )
    target_id = created.json()["id"]
    engine = create_engine(tokens["migration_url"])
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE targets SET authorization_expiry = NOW() - INTERVAL '1 minute' "
                "WHERE id = :target_id"
            ),
            {"target_id": target_id},
        )
    engine.dispose()

    expired = client.get(
        f"/api/v1/targets/{target_id}/eligibility",
        headers=auth(tokens["admin"]),
    )
    assert expired.status_code == 200
    assert expired.json()["eligible"] is False
    assert expired.json()["authorization_status"] == "expired"
    assert "authorization_expired" in expired.json()["reasons"]

    denied = client.post(
        "/api/v1/cases",
        headers=auth(tokens["admin"]),
        json={"target_id": target_id, "reason": "Open a case after expiry."},
    )
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "target_not_eligible"

    restored = create_engine(tokens["migration_url"])
    with restored.begin() as connection:
        connection.execute(
            text(
                "UPDATE targets SET authorization_expiry = NOW() + INTERVAL '1 day' "
                "WHERE id = :target_id"
            ),
            {"target_id": target_id},
        )
    restored.dispose()

    opened = client.post(
        "/api/v1/cases",
        headers=auth(tokens["admin"]),
        json={"target_id": target_id, "reason": "Open a case while authorization is valid."},
    )
    assert opened.status_code == 201
    case_id = opened.json()["id"]
    assert opened.json()["state"] == "AUTHORIZED_TARGET"
    assert opened.json()["created_by"] == "test-admin"

    revocation = client.post(
        f"/api/v1/targets/{target_id}/revocation",
        headers=auth(tokens["admin"]),
    )
    assert revocation.status_code == 200
    assert revocation.json()["authorization_status"] == "revoked"
    assert revocation.json()["eligible"] is False

    blocked = client.post(
        f"/api/v1/cases/{case_id}/transitions",
        headers=auth(tokens["admin"]),
        json={"to_state": "OBSERVATION", "reason": "Attempt to advance after revocation."},
    )
    assert blocked.status_code == 409
    assert "authorization_revoked" in blocked.json()["error"]["details"]["reasons"]
    current = client.get(f"/api/v1/cases/{case_id}", headers=auth(tokens["viewer"]))
    assert current.json()["state"] == "AUTHORIZED_TARGET"


def test_case_transitions_follow_the_pipeline_and_do_not_execute(client, tokens) -> None:
    created = client.post(
        "/api/v1/targets",
        headers=auth(tokens["admin"]),
        json=target_payload(),
    )
    target_id = created.json()["id"]
    opened = client.post(
        "/api/v1/cases",
        headers=auth(tokens["admin"]),
        json={"target_id": target_id, "reason": "Record a laboratory case."},
    )
    case_id = opened.json()["id"]

    skipped = client.post(
        f"/api/v1/cases/{case_id}/transitions",
        headers=auth(tokens["admin"]),
        json={"to_state": "ACTION", "reason": "Skip ahead."},
    )
    assert skipped.status_code == 409
    assert skipped.json()["error"]["code"] == "invalid_transition"
    assert skipped.json()["error"]["details"]["allowed_to_state"] == "OBSERVATION"

    for state in PIPELINE:
        moved = client.post(
            f"/api/v1/cases/{case_id}/transitions",
            headers=auth(tokens["admin"]),
            json={"to_state": state, "reason": f"Record transition to {state}."},
        )
        assert moved.status_code == 200
        body = moved.json()
        assert body["state"] == state
        assert body["transitions"][-1]["executed"] is False
        assert body["transitions"][-1]["to_state"] == state

    sealed = client.post(
        f"/api/v1/cases/{case_id}/transitions",
        headers=auth(tokens["admin"]),
        json={"to_state": "SEALED_AUDIT", "reason": "Terminal state has no successor."},
    )
    assert sealed.status_code == 409
    assert sealed.json()["error"]["details"]["allowed_to_state"] is None

    missing = client.post(
        "/api/v1/cases",
        headers=auth(tokens["admin"]),
        json={"target_id": str(uuid4()), "reason": "Unknown target."},
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "target_not_found"


def test_audit_chain_links_and_verifies(client, tokens) -> None:
    client.post("/api/v1/targets", headers=auth(tokens["admin"]), json=target_payload())
    created = client.post(
        "/api/v1/targets",
        headers=auth(tokens["admin"]),
        json=target_payload(
            name="lab-app-2",
            scope={
                "environment": "development",
                "assets": ["lab-app-2.internal"],
                "description": "Second owned development fixture.",
            },
        ),
    )
    assert created.status_code == 201
    events = client.get("/api/v1/audit/events", headers=auth(tokens["admin"]))
    items = events.json()["items"]
    assert len(items) == 2
    assert items[0]["sequence"] == 1
    assert items[1]["sequence"] == 2
    assert items[1]["previous_event_hash"] == items[0]["event_hash"]

    verified = client.get("/api/v1/audit/verify", headers=auth(tokens["viewer"]))
    assert verified.status_code == 200
    assert verified.json()["valid"] is True
    assert verified.json()["event_count"] == 2
    assert verified.json()["head_hash"] == items[1]["event_hash"]

    detail = client.get(f"/api/v1/audit/events/{items[0]['id']}", headers=auth(tokens["viewer"]))
    assert detail.status_code == 200
    assert detail.json()["event_hash"] == items[0]["event_hash"]


def test_empty_audit_chain_verifies(client, tokens) -> None:
    verified = client.get("/api/v1/audit/verify", headers=auth(tokens["viewer"]))
    assert verified.status_code == 200
    assert verified.json() == {
        "valid": True,
        "event_count": 0,
        "head_hash": None,
        "failure_sequence": None,
        "failure_reason": None,
        "contract_version": "1.0.0",
    }


def _insert_probe(connection) -> None:
    connection.execute(
        text(
            """
            INSERT INTO audit_events (
                id, sequence, event_timestamp, actor, event_type,
                target_id, case_id, payload, previous_event_hash, event_hash
            ) VALUES (
                :event_id, 9000000001, NOW(), 'owner-test', 'test.probe',
                NULL, NULL, '{}'::jsonb, :previous, :digest
            )
            """
        ),
        {
            "event_id": "44444444-4444-4444-8444-444444444444",
            "previous": "0" * 64,
            "digest": "ab" * 32,
        },
    )


def test_audit_events_cannot_be_updated_or_deleted(tokens) -> None:
    owner = create_engine(tokens["migration_url"])
    with owner.connect() as connection:
        transaction = connection.begin()
        _insert_probe(connection)
        with pytest.raises(DBAPIError, match="append-only"):
            connection.execute(text("UPDATE audit_events SET actor = 'tampered'"))
        transaction.rollback()
    with owner.connect() as connection:
        transaction = connection.begin()
        _insert_probe(connection)
        with pytest.raises(DBAPIError, match="append-only"):
            connection.execute(text("DELETE FROM audit_events"))
        transaction.rollback()
    with owner.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DBAPIError, match="append-only"):
            connection.execute(text("TRUNCATE TABLE audit_events"))
        transaction.rollback()
    owner.dispose()

    application = create_engine(tokens["app_url"])
    with application.connect() as connection:
        with pytest.raises(DBAPIError) as denied:
            connection.execute(text("UPDATE audit_events SET actor = 'tampered'"))
            connection.commit()
    message = str(denied.value).lower()
    assert "permission denied" in message or "append-only" in message
    application.dispose()


def test_audit_http_delete_is_not_available(client, tokens) -> None:
    response = client.delete("/api/v1/audit/events", headers=auth(tokens["admin"]))
    assert response.status_code == 405
