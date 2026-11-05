"""Shared bounds for operator-supplied strings."""

from typing import Annotated

from pydantic import Field

BoundedName = Annotated[str, Field(min_length=1, max_length=200)]
BoundedReason = Annotated[str, Field(min_length=1, max_length=1000)]
BoundedDescription = Annotated[str, Field(min_length=1, max_length=500)]


def reject_unbounded_text(value: str) -> str:
    """Reject whitespace padding and control characters."""
    if value != value.strip():
        raise ValueError("must not include leading or trailing whitespace")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("must not include control characters")
    return value
