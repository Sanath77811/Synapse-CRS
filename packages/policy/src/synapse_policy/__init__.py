"""Authorization decisions for registered targets."""

from synapse_policy.decision import (
    AuthorizationDecision,
    TargetRecord,
    effective_status,
    evaluate_authorization,
)

__all__ = [
    "AuthorizationDecision",
    "TargetRecord",
    "effective_status",
    "evaluate_authorization",
]
