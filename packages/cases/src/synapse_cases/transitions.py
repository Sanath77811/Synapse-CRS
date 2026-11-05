"""Linear case transitions for the v0.1 pipeline model.

The only accepted path is:

AUTHORIZED_TARGET -> OBSERVATION -> EVIDENCE -> HYPOTHESIS -> VERIFICATION
-> APPROVAL -> ACTION -> VALIDATION -> ROLLBACK -> SEALED_AUDIT

SEALED_AUDIT is terminal. v0.1 does not define cancel, skip, or early
rollback transitions.
"""

from synapse_contracts.cases import CaseState


class InvalidTransition(Exception):
    """Raised when a case is not allowed to enter the proposed state."""

    def __init__(
        self,
        current: CaseState,
        proposed: CaseState,
        allowed: CaseState | None,
    ) -> None:
        self.current = current
        self.proposed = proposed
        self.allowed = allowed
        allowed_name = allowed.value if allowed is not None else None
        super().__init__(
            f"Cannot move from {current.value} to {proposed.value}; "
            f"allowed next state is {allowed_name}."
        )


FORWARD: dict[CaseState, CaseState] = {
    CaseState.AUTHORIZED_TARGET: CaseState.OBSERVATION,
    CaseState.OBSERVATION: CaseState.EVIDENCE,
    CaseState.EVIDENCE: CaseState.HYPOTHESIS,
    CaseState.HYPOTHESIS: CaseState.VERIFICATION,
    CaseState.VERIFICATION: CaseState.APPROVAL,
    CaseState.APPROVAL: CaseState.ACTION,
    CaseState.ACTION: CaseState.VALIDATION,
    CaseState.VALIDATION: CaseState.ROLLBACK,
    CaseState.ROLLBACK: CaseState.SEALED_AUDIT,
}


def allowed_next(current: CaseState) -> CaseState | None:
    return FORWARD.get(current)


def ensure_transition(current: CaseState, proposed: CaseState) -> None:
    allowed = allowed_next(current)
    if allowed is None or proposed != allowed:
        raise InvalidTransition(current, proposed, allowed)
