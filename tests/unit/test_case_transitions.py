"""Case transitions are a pure state machine with one forward edge."""

import pytest
from synapse_cases import FORWARD, InvalidTransition, allowed_next, ensure_transition
from synapse_contracts.cases import CaseState


def test_forward_path_matches_the_v0_1_pipeline() -> None:
    expected = [
        CaseState.AUTHORIZED_TARGET,
        CaseState.OBSERVATION,
        CaseState.EVIDENCE,
        CaseState.HYPOTHESIS,
        CaseState.VERIFICATION,
        CaseState.APPROVAL,
        CaseState.ACTION,
        CaseState.VALIDATION,
        CaseState.ROLLBACK,
        CaseState.SEALED_AUDIT,
    ]
    current = expected[0]
    for nxt in expected[1:]:
        assert allowed_next(current) is nxt
        ensure_transition(current, nxt)
        current = nxt
    assert allowed_next(CaseState.SEALED_AUDIT) is None
    assert set(FORWARD) == set(expected[:-1])


def test_skip_and_reverse_transitions_are_rejected() -> None:
    with pytest.raises(InvalidTransition) as skipped:
        ensure_transition(CaseState.AUTHORIZED_TARGET, CaseState.ACTION)
    assert skipped.value.allowed is CaseState.OBSERVATION

    with pytest.raises(InvalidTransition):
        ensure_transition(CaseState.EVIDENCE, CaseState.OBSERVATION)

    with pytest.raises(InvalidTransition) as terminal:
        ensure_transition(CaseState.SEALED_AUDIT, CaseState.ROLLBACK)
    assert terminal.value.allowed is None


def test_self_transition_is_rejected() -> None:
    with pytest.raises(InvalidTransition):
        ensure_transition(CaseState.OBSERVATION, CaseState.OBSERVATION)
