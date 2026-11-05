"""Structured diagnostic logging. Values are field names and small integers."""

import json
import logging
import sys
from typing import Any

_SECRET_KEYS = frozenset(
    {
        "signature",
        "private",
        "pem",
        "token",
        "password",
        "secret",
        "authorization",
        "key",
    }
)

logger = logging.getLogger("synapse.agent")


def configure_logging() -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_event(event: str, **fields: Any) -> None:
    payload: dict[str, Any] = {"event": event}
    for name, value in fields.items():
        lowered = name.lower()
        if any(part in lowered for part in _SECRET_KEYS):
            continue
        payload[name] = value
    logger.info(json.dumps(payload, separators=(",", ":"), default=str))
