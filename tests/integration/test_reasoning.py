"""PostgreSQL persistence and HTTP access for hybrid reasoning."""

from uuid import uuid4

from synapse_telemetry.normalization import normalize_observation
from synapse_telemetry.signatures import generate_signing_key, sign_event

from tests.integration.helpers import auth
from tests.integration.test_agent_enrollment import _create_target, _enroll
from tests.integration.test_telemetry_store import _raw

FIXED = "2026-09-29T17:34:00.000000Z"


def test_reasoning_assessment_round_trip(client, tokens) -> None:
    key = generate_signing_key()
    target_id = _create_target(client, tokens)
    agent_id = str(uuid4())
    boot_id = str(uuid4())
    enrolled = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
    assert enrolled.status_code == 201
    start = normalize_observation(
        _raw(
            target_id=target_id,
            agent_id=agent_id,
            boot_id=boot_id,
            sequence=1,
            pid=20,
            start_ticks=9,
            observed_at=FIXED,
        )
    )
    assert (
        client.post(
            "/api/v1/telemetry/ingest",
            json={"envelope": start.model_dump(mode="json"), "signature": sign_event(key, start)},
        ).status_code
        == 201
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
                remote_address="[ip]",
                uid=1000,
                pid=20,
            )
        )
        response = client.post(
            "/api/v1/telemetry/ingest",
            json={
                "envelope": envelope.model_dump(mode="json"),
                "signature": sign_event(key, envelope),
            },
        )
        assert response.status_code == 201, response.text
    correlated = client.post(
        f"/api/v1/targets/{target_id}/correlation/runs",
        headers=auth(tokens["admin"]),
        json={"window_seconds": 300},
    )
    assert correlated.status_code == 201
    viewer_blocked = client.post(
        f"/api/v1/targets/{target_id}/reasoning/assessments",
        headers=auth(tokens["viewer"]),
        json={"window_seconds": 300, "dataset_label": "synthetic_lab"},
    )
    assert viewer_blocked.status_code == 403
    created = client.post(
        f"/api/v1/targets/{target_id}/reasoning/assessments",
        headers=auth(tokens["admin"]),
        json={"window_seconds": 300, "dataset_label": "synthetic_lab"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert "signature" not in body
    assert body["dataset_label"] == "synthetic_lab"
    assert body["selected_hypothesis"].startswith("H")
    assert body["neural"]["limitations"]
    first_id = body["id"]
    again = client.post(
        f"/api/v1/targets/{target_id}/reasoning/assessments",
        headers=auth(tokens["admin"]),
        json={"window_seconds": 300, "dataset_label": "synthetic_lab"},
    )
    assert again.status_code == 201
    listed = client.get(
        f"/api/v1/targets/{target_id}/reasoning/assessments",
        headers=auth(tokens["viewer"]),
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    detail = client.get(
        f"/api/v1/reasoning/assessments/{first_id}",
        headers=auth(tokens["viewer"]),
    )
    assert detail.status_code == 200
    timeline = client.get(
        f"/api/v1/reasoning/assessments/{first_id}/timeline",
        headers=auth(tokens["viewer"]),
    )
    assert timeline.status_code == 200
    assert timeline.json()["timeline"]
    unsafe = client.post(
        f"/api/v1/reasoning/assessments/{first_id}/decision-proposals/verify",
        headers=auth(tokens["admin"]),
        json={
            "kind": "execute_host_mitigation",
            "authorized": True,
            "in_scope": True,
            "human_approved": True,
        },
    )
    assert unsafe.status_code == 201
    assert unsafe.json()["solver_result"] == "unsat"


def test_unauthenticated_reasoning_is_rejected(client, tokens) -> None:
    target_id = _create_target(client, tokens)
    response = client.get(f"/api/v1/targets/{target_id}/reasoning/assessments")
    assert response.status_code == 401
