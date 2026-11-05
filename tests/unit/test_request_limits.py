"""Request guards reject oversized and non-JSON ingest bodies."""

import asyncio

from synapse_api.limits import RequestGuardMiddleware


async def _ok_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def _run(scope: dict) -> list[dict]:
    messages: list[dict] = []

    async def send(message: dict) -> None:
        messages.append(message)

    async def receive() -> dict:
        return {"type": "http.request", "body": b"{}", "more_body": False}

    app = RequestGuardMiddleware(_ok_app, max_bytes=64)
    asyncio.run(app(scope, receive, send))
    return messages


def _scope(*, method: str, path: str, headers: list[tuple[bytes, bytes]]) -> dict:
    return {"type": "http", "method": method, "path": path, "headers": headers}


def test_post_without_content_length_is_rejected() -> None:
    messages = _run(_scope(method="POST", path="/api/v1/targets", headers=[]))
    assert messages[0]["status"] == 411


def test_oversize_content_length_is_rejected() -> None:
    messages = _run(
        _scope(
            method="POST",
            path="/api/v1/telemetry/ingest",
            headers=[
                (b"content-length", b"100"),
                (b"content-type", b"application/json"),
            ],
        )
    )
    assert messages[0]["status"] == 413
    assert b"payload_too_large" in messages[1]["body"]


def test_ingest_rejects_non_json_content_type() -> None:
    messages = _run(
        _scope(
            method="POST",
            path="/api/v1/telemetry/ingest",
            headers=[
                (b"content-length", b"2"),
                (b"content-type", b"text/plain"),
            ],
        )
    )
    assert messages[0]["status"] == 415


def test_json_ingest_within_limit_is_passed() -> None:
    messages = _run(
        _scope(
            method="POST",
            path="/api/v1/telemetry/ingest",
            headers=[
                (b"content-length", b"2"),
                (b"content-type", b"application/json; charset=utf-8"),
            ],
        )
    )
    assert messages[0]["status"] == 200
