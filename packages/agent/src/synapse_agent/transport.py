"""POST signed envelopes to the Phase 6 ingest URL using urllib."""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

from synapse_agent.log import log_event

OutcomeKind = Literal["accepted", "duplicate", "transient", "permanent"]

PERMANENT_STATUS = {400, 401, 403, 409, 413, 415, 422}
TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}


@dataclass(frozen=True)
class TransportResult:
    kind: OutcomeKind
    status_code: int | None
    code: str | None = None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


def post_ingest(
    url: str,
    envelope: dict[str, Any],
    signature: str,
    *,
    timeout: float,
) -> TransportResult:
    payload = json.dumps({"envelope": envelope, "signature": signature}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            status = int(response.getcode() or 0)
            body = response.read(2048)
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        try:
            body = exc.read(2048)
        except OSError:
            body = b""
    except urllib.error.URLError:
        log_event("ingest_transport_error")
        return TransportResult(kind="transient", status_code=None, code="transport_error")
    except TimeoutError:
        log_event("ingest_timeout")
        return TransportResult(kind="transient", status_code=None, code="timeout")
    code = _error_code(body)
    if status in {200, 201}:
        kind: OutcomeKind = "duplicate" if status == 200 else "accepted"
        log_event("ingest_ok", status=status, persistence=kind)
        return TransportResult(kind=kind, status_code=status, code=code)
    if status in PERMANENT_STATUS:
        log_event("ingest_rejected", status=status, code=code)
        return TransportResult(kind="permanent", status_code=status, code=code)
    log_event("ingest_transient", status=status, code=code)
    return TransportResult(kind="transient", status_code=status, code=code)


def _error_code(body: bytes) -> str | None:
    if not body:
        return None
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    error = parsed.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    if isinstance(code, str) and 1 <= len(code) <= 80:
        return code
    return None
