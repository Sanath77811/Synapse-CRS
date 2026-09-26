"""Authorization decisions fail closed without a database."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from synapse_contracts.scope import TargetScope
from synapse_policy import TargetRecord, effective_status, evaluate_authorization

NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def _record(**overrides: object) -> TargetRecord:
    scope = TargetScope(
        environment="lab",
        assets=["lab-app-1.internal"],
        description="Owned laboratory application fixture.",
    )
    base = TargetRecord(
        target_id=uuid4(),
        owner="research-team",
        stored_status="active",
        authorization_expiry=NOW + timedelta(days=1),
        capabilities=("telemetry.ingest",),
        scope=scope,
    )
    data = {
        "target_id": base.target_id,
        "owner": base.owner,
        "stored_status": base.stored_status,
        "authorization_expiry": base.authorization_expiry,
        "capabilities": base.capabilities,
        "scope": base.scope,
        "scope_reasons": base.scope_reasons,
    }
    data.update(overrides)
    return TargetRecord(**data)  # type: ignore[arg-type]


def test_active_target_is_eligible() -> None:
    decision = evaluate_authorization(_record(), NOW)
    assert decision.eligible is True
    assert decision.reasons == ()
    assert decision.authorization_status == "active"


def test_expired_authorization_is_not_eligible() -> None:
    decision = evaluate_authorization(
        _record(authorization_expiry=NOW - timedelta(seconds=1)),
        NOW,
    )
    assert decision.eligible is False
    assert "authorization_expired" in decision.reasons
    assert decision.authorization_status == "expired"


def test_revoked_authorization_is_not_eligible() -> None:
    decision = evaluate_authorization(_record(stored_status="revoked"), NOW)
    assert decision.eligible is False
    assert "authorization_revoked" in decision.reasons
    assert decision.authorization_status == "revoked"


def test_expiry_equal_to_now_is_expired() -> None:
    decision = evaluate_authorization(_record(authorization_expiry=NOW), NOW)
    assert decision.eligible is False
    assert decision.authorization_status == "expired"


def test_naive_expiry_fails_closed() -> None:
    decision = evaluate_authorization(
        _record(authorization_expiry=datetime(2026, 12, 1, 0, 0)),
        NOW,
    )
    assert decision.eligible is False
    assert "authorization_expired" in decision.reasons


def test_empty_capabilities_fail_closed() -> None:
    decision = evaluate_authorization(_record(capabilities=()), NOW)
    assert decision.eligible is False
    assert "capabilities_empty" in decision.reasons


def test_unknown_capability_fails_closed() -> None:
    decision = evaluate_authorization(_record(capabilities=("shell.execute",)), NOW)
    assert decision.eligible is False
    assert "capabilities_not_allowed" in decision.reasons


def test_invalid_scope_fails_closed() -> None:
    decision = evaluate_authorization(
        _record(scope=None, scope_reasons=("scope_invalid",)),
        NOW,
    )
    assert decision.eligible is False
    assert "scope_invalid" in decision.reasons


def test_unknown_stored_status_is_invalid() -> None:
    assert effective_status("pending", NOW + timedelta(days=1), NOW) == "invalid"
    decision = evaluate_authorization(_record(stored_status="pending"), NOW)
    assert decision.eligible is False
    assert decision.authorization_status == "invalid"
