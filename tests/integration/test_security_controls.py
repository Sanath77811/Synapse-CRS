"""Database privileges, row locks, and audit-head checks."""

import os
import time
from pathlib import Path
from threading import Thread
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from synapse_api.errors import ApiError
from synapse_api.services import create_case, revoke_target, transition_case
from synapse_audit import GENESIS_HASH
from synapse_contracts.cases import CaseCreate, CaseState, CaseTransitionRequest

from tests.integration.helpers import auth, target_payload

ROOT = Path(__file__).resolve().parents[2]


def _app_engine(tokens: dict[str, str]):
    return create_engine(tokens["app_url"])


def _open_target_and_case(client, tokens) -> tuple[str, str]:
    created = client.post(
        "/api/v1/targets",
        headers=auth(tokens["admin"]),
        json=target_payload(),
    )
    assert created.status_code == 201
    target_id = created.json()["id"]
    opened = client.post(
        "/api/v1/cases",
        headers=auth(tokens["admin"]),
        json={"target_id": target_id, "reason": "Open a case for a privilege check."},
    )
    assert opened.status_code == 201
    return target_id, opened.json()["id"]


def _wait_for_target_lock(connection) -> bool:
    """Return once a transaction is waiting on the holder's row lock.

    PostgreSQL represents that wait as an ungranted transactionid lock.
    The watcher must be able to see other sessions' lock rows, so tests use
    the migration role. synapse_app cannot see them.
    """
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        waiting = connection.execute(
            text(
                """
                SELECT count(*) FROM pg_locks
                WHERE NOT granted AND locktype = 'transactionid'
                """
            )
        ).scalar()
        if waiting:
            return True
        time.sleep(0.05)
    return False


def test_app_role_cannot_restore_or_skip_state(client, tokens) -> None:
    target_id, case_id = _open_target_and_case(client, tokens)
    application = _app_engine(tokens)
    with pytest.raises(DBAPIError) as expiry:
        with application.begin() as connection:
            connection.execute(
                text(
                    "UPDATE targets SET authorization_expiry = NOW() + INTERVAL '10 years' "
                    "WHERE id = :target_id"
                ),
                {"target_id": target_id},
            )
    assert "permission denied" in str(expiry.value).lower()

    with pytest.raises(DBAPIError) as skipped:
        with application.begin() as connection:
            connection.execute(
                text("UPDATE cases SET state = 'ACTION' WHERE id = :case_id"),
                {"case_id": case_id},
            )
    assert "case transition is not allowed" in str(skipped.value)

    with application.begin() as connection:
        connection.execute(
            text("UPDATE cases SET state = 'OBSERVATION', updated_at = NOW() WHERE id = :case_id"),
            {"case_id": case_id},
        )
    current = client.get(f"/api/v1/cases/{case_id}", headers=auth(tokens["viewer"]))
    assert current.json()["state"] == "OBSERVATION"

    with pytest.raises(DBAPIError) as inserted:
        with application.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO cases (
                        id, target_id, state, created_at, updated_at, created_by
                    )
                    VALUES (
                        :case_id, :target_id, 'ACTION', NOW(), NOW(), 'intruder'
                    )
                    """
                ),
                {"case_id": str(uuid4()), "target_id": target_id},
            )
    assert "case transition is not allowed" in str(inserted.value)

    revoked = client.post(
        f"/api/v1/targets/{target_id}/revocation",
        headers=auth(tokens["admin"]),
    )
    assert revoked.status_code == 200
    with pytest.raises(DBAPIError) as restored:
        with application.begin() as connection:
            connection.execute(
                text("UPDATE targets SET authorization_status = 'active' WHERE id = :target_id"),
                {"target_id": target_id},
            )
    assert "authorization revocation is one-way" in str(restored.value)
    still = client.get(f"/api/v1/targets/{target_id}", headers=auth(tokens["viewer"]))
    assert still.json()["authorization_status"] == "revoked"
    application.dispose()


def test_verify_rejects_a_rewritten_chain_head(client, tokens) -> None:
    created = client.post(
        "/api/v1/targets",
        headers=auth(tokens["admin"]),
        json=target_payload(),
    )
    assert created.status_code == 201
    before = client.get("/api/v1/audit/verify", headers=auth(tokens["viewer"]))
    assert before.json()["valid"] is True
    real_head = before.json()["head_hash"]

    application = _app_engine(tokens)
    with application.begin() as connection:
        connection.execute(
            text("UPDATE audit_chain_state SET head_hash = :head WHERE id = 1"),
            {"head": "ab" * 32},
        )
    mismatched = client.get("/api/v1/audit/verify", headers=auth(tokens["viewer"]))
    assert mismatched.status_code == 200
    assert mismatched.json()["valid"] is False
    assert mismatched.json()["failure_reason"] == "head_hash_mismatch"
    assert mismatched.json()["head_hash"] is None

    with application.begin() as connection:
        connection.execute(
            text("UPDATE audit_chain_state SET head_hash = :head, next_sequence = 99 WHERE id = 1"),
            {"head": real_head},
        )
    drifted = client.get("/api/v1/audit/verify", headers=auth(tokens["viewer"]))
    assert drifted.json()["valid"] is False
    assert drifted.json()["failure_reason"] == "chain_state_mismatch"
    application.dispose()


def test_verify_rejects_an_empty_chain_with_the_wrong_head(client, tokens) -> None:
    application = _app_engine(tokens)
    with application.begin() as connection:
        connection.execute(
            text("UPDATE audit_chain_state SET head_hash = :head WHERE id = 1"),
            {"head": "cd" * 32},
        )
    mismatched = client.get("/api/v1/audit/verify", headers=auth(tokens["viewer"]))
    assert mismatched.json()["valid"] is False
    assert mismatched.json()["failure_reason"] == "head_hash_mismatch"
    assert mismatched.json()["event_count"] == 0

    with application.begin() as connection:
        connection.execute(
            text(
                "UPDATE audit_chain_state SET head_hash = :genesis, next_sequence = 4 WHERE id = 1"
            ),
            {"genesis": GENESIS_HASH},
        )
    drifted = client.get("/api/v1/audit/verify", headers=auth(tokens["viewer"]))
    assert drifted.json()["valid"] is False
    assert drifted.json()["failure_reason"] == "chain_state_mismatch"
    application.dispose()


def test_revocation_blocks_a_case_create_waiting_on_the_target_lock(client, tokens) -> None:
    created = client.post(
        "/api/v1/targets",
        headers=auth(tokens["admin"]),
        json=target_payload(),
    )
    target_id = UUID(created.json()["id"])
    application = _app_engine(tokens)
    owner = create_engine(tokens["migration_url"])
    holder = application.connect()
    watch = owner.connect()
    transaction = holder.begin()
    outcome: list[str] = []

    def worker() -> None:
        session = Session(application)
        session.execute(text("SET lock_timeout = '15s'"))
        try:
            create_case(
                session,
                CaseCreate(target_id=target_id, reason="Open while revocation is committing."),
                "test-admin",
            )
            session.commit()
            outcome.append("created")
        except ApiError as exc:
            session.rollback()
            outcome.append(exc.code)
        except Exception as exc:
            session.rollback()
            outcome.append(type(exc).__name__)
        finally:
            session.close()

    try:
        holder.execute(
            text("SELECT id FROM targets WHERE id = :target_id FOR UPDATE"),
            {"target_id": target_id},
        )
        thread = Thread(target=worker)
        thread.start()
        saw_wait = _wait_for_target_lock(watch)
        holder.execute(
            text(
                "UPDATE targets SET authorization_status = 'revoked', updated_at = NOW() "
                "WHERE id = :target_id"
            ),
            {"target_id": target_id},
        )
        transaction.commit()
        thread.join(timeout=15)
    finally:
        if transaction.is_active:
            transaction.rollback()
        holder.close()
        watch.close()
        application.dispose()
        owner.dispose()

    assert saw_wait
    assert outcome == ["target_not_eligible"]
    cases = client.get("/api/v1/cases", headers=auth(tokens["admin"]))
    assert cases.json()["total"] == 0


def test_revocation_blocks_a_transition_waiting_on_the_target_lock(client, tokens) -> None:
    target_id, case_id = _open_target_and_case(client, tokens)
    target_uuid = UUID(target_id)
    case_uuid = UUID(case_id)
    application = _app_engine(tokens)
    owner = create_engine(tokens["migration_url"])
    holder = application.connect()
    watch = owner.connect()
    transaction = holder.begin()
    outcome: list[str] = []

    def worker() -> None:
        session = Session(application)
        session.execute(text("SET lock_timeout = '15s'"))
        try:
            transition_case(
                session,
                case_uuid,
                CaseTransitionRequest(
                    to_state=CaseState.OBSERVATION,
                    reason="Advance while revocation is committing.",
                ),
                "test-admin",
            )
            session.commit()
            outcome.append("advanced")
        except ApiError as exc:
            session.rollback()
            outcome.append(exc.code)
        except Exception as exc:
            session.rollback()
            outcome.append(type(exc).__name__)
        finally:
            session.close()

    try:
        holder.execute(
            text("SELECT id FROM targets WHERE id = :target_id FOR UPDATE"),
            {"target_id": target_uuid},
        )
        thread = Thread(target=worker)
        thread.start()
        saw_wait = _wait_for_target_lock(watch)
        holder.execute(
            text(
                "UPDATE targets SET authorization_status = 'revoked', updated_at = NOW() "
                "WHERE id = :target_id"
            ),
            {"target_id": target_uuid},
        )
        transaction.commit()
        thread.join(timeout=15)
    finally:
        if transaction.is_active:
            transaction.rollback()
        holder.close()
        watch.close()
        application.dispose()
        owner.dispose()

    assert saw_wait
    assert outcome == ["target_not_eligible"]
    current = client.get(f"/api/v1/cases/{case_id}", headers=auth(tokens["viewer"]))
    assert current.json()["state"] == "AUTHORIZED_TARGET"


def test_concurrent_revokes_record_one_event(client, tokens) -> None:
    created = client.post(
        "/api/v1/targets",
        headers=auth(tokens["admin"]),
        json=target_payload(),
    )
    target_id = UUID(created.json()["id"])
    application = _app_engine(tokens)
    outcome: list[str] = []

    def worker() -> None:
        session = Session(application)
        try:
            revoke_target(session, target_id, "test-admin")
            session.commit()
            outcome.append("revoked")
        except ApiError as exc:
            session.rollback()
            outcome.append(exc.code)
        finally:
            session.close()

    threads = [Thread(target=worker), Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert sorted(outcome) == ["revoked", "target_already_revoked"]
    with application.connect() as connection:
        count = connection.execute(
            text(
                "SELECT count(*) FROM audit_events "
                "WHERE event_type = 'target.revoked' AND target_id = :target_id"
            ),
            {"target_id": target_id},
        ).scalar()
    assert count == 1
    application.dispose()


def test_migration_fails_when_synapse_app_is_absent(database) -> None:
    from synapse_api.db import reset_engine

    reset_engine()
    probe_name = "synapse_role_probe"
    admin = create_engine(
        make_url(database["migration_url"]).set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    renamed = False
    previous = os.environ.get("MIGRATION_DATABASE_URL")
    try:
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {probe_name} WITH (FORCE)"))
            connection.execute(text(f"CREATE DATABASE {probe_name}"))
            connection.execute(text("ALTER ROLE synapse_app RENAME TO synapse_app_held"))
            renamed = True
        probe_url = (
            make_url(database["migration_url"])
            .set(database=probe_name)
            .render_as_string(hide_password=False)
        )
        os.environ["MIGRATION_DATABASE_URL"] = probe_url
        config = Config(str(ROOT / "apps" / "api" / "alembic.ini"))
        with pytest.raises(Exception) as failure:
            command.upgrade(config, "head")
        assert "synapse_app role must exist before privileges are granted" in str(failure.value)
    finally:
        if previous is None:
            os.environ.pop("MIGRATION_DATABASE_URL", None)
        else:
            os.environ["MIGRATION_DATABASE_URL"] = previous
        with admin.connect() as connection:
            if renamed:
                connection.execute(text("ALTER ROLE synapse_app_held RENAME TO synapse_app"))
            connection.execute(text(f"DROP DATABASE IF EXISTS {probe_name} WITH (FORCE)"))
        admin.dispose()
        reset_engine()
