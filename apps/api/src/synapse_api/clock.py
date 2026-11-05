"""Clock access kept in one place so tests can reason about expiry."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)
