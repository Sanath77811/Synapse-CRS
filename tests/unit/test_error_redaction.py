"""Unexpected failures stay generic in responses and logs."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from synapse_api.errors import logger, register_exception_handlers


def test_unexpected_database_error_does_not_leak_the_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    app = FastAPI()
    register_exception_handlers(app)
    secret = "postgresql+psycopg://synapse_app:super-secret-db@postgres:5432/synapse"
    calls: list[tuple[object, ...]] = []

    def spy(message: str, *args: object, **kwargs: object) -> None:
        calls.append((message, args, kwargs))

    monkeypatch.setattr(logger, "error", spy)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError(secret)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "super-secret-db" not in response.text
    assert "postgresql" not in response.text.lower()
    rendered = " ".join(str(part) for call in calls for part in call)
    assert secret not in rendered
    assert "postgresql" not in rendered.lower()
    assert calls == [("request failed error_type=%s", ("RuntimeError",), {})]
