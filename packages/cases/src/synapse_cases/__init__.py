"""Case state machine. Transitions are validated here and executed nowhere."""

from synapse_cases.transitions import (
    FORWARD,
    InvalidTransition,
    allowed_next,
    ensure_transition,
)

__all__ = [
    "FORWARD",
    "InvalidTransition",
    "allowed_next",
    "ensure_transition",
]
