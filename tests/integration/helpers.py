"""Request builders for integration tests."""

from datetime import UTC, datetime, timedelta


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def target_payload(**overrides: object) -> dict:
    expiry = datetime.now(UTC) + timedelta(days=30)
    body: dict = {
        "name": "lab-app-1",
        "owner": "research-team",
        "scope": {
            "environment": "lab",
            "assets": ["lab-app-1.internal"],
            "description": "Owned laboratory application fixture.",
        },
        "authorization_expiry": expiry.isoformat(),
        "allowed_capabilities": ["telemetry.ingest"],
    }
    body.update(overrides)
    return body
