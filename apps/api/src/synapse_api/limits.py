"""Request-size and content-type safeguards for the API process.

These checks are process-local. They bound each request; they are not a
distributed rate limiter.
"""

import json

from starlette.types import ASGIApp, Receive, Scope, Send

from synapse_api.errors import error_body

INGEST_PATH = "/api/v1/telemetry/ingest"
JSON_TYPE = b"application/json"


def _header(scope: Scope, name: bytes) -> bytes | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value
    return None


async def _json_error(send: Send, status: int, code: str, message: str) -> None:
    body = json.dumps(error_body(code, message), separators=(",", ":")).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestGuardMiddleware:
    """Reject oversized bodies and non-JSON ingest requests before routing."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "GET")
        path = scope.get("path", "")
        if method in {"POST", "PUT", "PATCH"}:
            raw_length = _header(scope, b"content-length")
            if raw_length is None:
                await _json_error(
                    send,
                    411,
                    "length_required",
                    "POST requests must include Content-Length.",
                )
                return
            try:
                length = int(raw_length.decode("ascii"))
            except ValueError:
                await _json_error(send, 400, "invalid_request", "Request size is invalid.")
                return
            if length < 0 or length > self.max_bytes:
                await _json_error(
                    send,
                    413,
                    "payload_too_large",
                    "The request body exceeds the configured size limit.",
                )
                return
        if method == "POST" and path == INGEST_PATH:
            content_type = _header(scope, b"content-type") or b""
            media_type = content_type.split(b";", 1)[0].strip().lower()
            if media_type != JSON_TYPE:
                await _json_error(
                    send,
                    415,
                    "unsupported_media_type",
                    "Telemetry ingest requires application/json.",
                )
                return
        await self.app(scope, receive, send)
