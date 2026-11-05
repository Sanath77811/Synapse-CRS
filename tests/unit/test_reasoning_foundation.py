"""Reconstruction, hybrid hypotheses, Isolation Forest, and Z3 policy checks."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from synapse_correlation.engine import correlate
from synapse_correlation.models import Observation
from synapse_reasoning.evaluation import evaluate_neural_holdout
from synapse_reasoning.pipeline import run_reasoning
from synapse_reasoning.reconstruction import reconstruct
from synapse_reasoning.verification import propose, verify_proposal

BASE = datetime(2026, 9, 29, 17, 34, tzinfo=UTC)
TARGET = uuid4()
AGENT = uuid4()
BOOT = uuid4()


def _obs(event_type: str, sequence: int, seconds: int, **payload: object) -> Observation:
    return Observation(
        event_id=uuid4(),
        event_type=event_type,
        target_id=TARGET,
        agent_id=AGENT,
        boot_id=BOOT,
        sequence=sequence,
        observed_at=BASE + timedelta(seconds=seconds),
        payload=payload,
    )


def _normal() -> tuple[Observation, ...]:
    return (
        _obs(
            "process_started",
            1,
            0,
            pid=10,
            ppid=1,
            uid=1000,
            start_ticks=1,
            comm="python3",
        ),
        _obs(
            "network_connection_observed",
            2,
            1,
            protocol="tcp",
            local_port=40000,
            remote_port=443,
            remote_address="[ip]",
            uid=1000,
            pid=10,
        ),
        _obs("process_exited", 3, 2, pid=10, start_ticks=1),
    )


def _busy() -> tuple[Observation, ...]:
    start = _obs(
        "process_started",
        1,
        0,
        pid=20,
        ppid=1,
        uid=1000,
        start_ticks=9,
        comm="python3",
    )
    nets = [
        _obs(
            "network_connection_observed",
            index + 2,
            index + 1,
            protocol="tcp",
            local_port=41000 + index,
            remote_port=80 + index,
            remote_address="[ip]",
            uid=1000,
            pid=20,
        )
        for index in range(6)
    ]
    return (start, *nets)


def test_timeline_marks_observed_versus_inferred() -> None:
    exited = _obs("process_exited", 1, 0, pid=50, start_ticks=3)
    reconstruction = reconstruct((exited,), (), (), created_at=BASE, dataset_label="synthetic_lab")
    classes = {item.classification for item in reconstruction.timeline}
    assert "observed" in classes
    assert "inferred" in classes
    inferred = next(item for item in reconstruction.timeline if item.classification == "inferred")
    assert inferred.event_id is None


def test_pid_not_joined_without_start_ticks() -> None:
    first = _obs("process_started", 1, 0, pid=9, ppid=1, uid=1000, start_ticks=1, comm="python3")
    second = _obs("process_started", 2, 1, pid=9, ppid=1, uid=1000, start_ticks=2, comm="python3")
    reconstruction = reconstruct(
        (first, second), (), (), created_at=BASE, dataset_label="synthetic_lab"
    )
    assert len(reconstruction.processes) == 2
    keys = {item.identity_key for item in reconstruction.processes}
    assert len(keys) == 2


def test_normal_pipeline_selects_non_malicious_hypothesis() -> None:
    observations = _normal()
    correlated = correlate(observations, created_at=BASE)
    _reconstruction, assessment = run_reasoning(
        observations,
        correlated.findings,
        correlated.links,
        created_at=BASE,
        dataset_label="synthetic_lab",
        window_seconds=300,
        include_counterfactual=False,
    )
    assert assessment.selected_hypothesis in {
        "H1_normal",
        "H2_unusual_legitimate",
        "H4_insufficient_evidence",
    }
    assert assessment.verification is not None
    assert assessment.verification.solver_result in {"sat", "unsat", "unknown"}
    assert "probability" not in assessment.neural.limitations or "not an attack" in (
        assessment.neural.limitations.lower()
    )


def test_busy_pattern_has_phase8_findings_and_explanation_event_ids() -> None:
    observations = _busy()
    correlated = correlate(observations, created_at=BASE)
    _reconstruction, assessment = run_reasoning(
        observations,
        correlated.findings,
        correlated.links,
        created_at=BASE,
        dataset_label="synthetic_lab",
        window_seconds=300,
        include_counterfactual=True,
    )
    assert correlated.findings
    assert assessment.explanation.event_ids
    assert assessment.counterfactual is not None
    assert assessment.counterfactual.kind == "feature_ablation"


def test_z3_rejects_host_mitigation() -> None:
    reconstruction = reconstruct(_normal(), (), (), created_at=BASE, dataset_label="synthetic_lab")
    proposal = propose(
        reconstruction,
        "execute_host_mitigation",
        authorized=True,
        in_scope=True,
        human_approved=True,
    )
    result = verify_proposal(proposal)
    assert result.solver_result == "unsat"
    assert result.status == "rejected_by_policy"
    assert "mitigation_kind_forbidden" in result.violated


def test_z3_accepts_investigation_recommendation() -> None:
    reconstruction = reconstruct(_normal(), (), (), created_at=BASE, dataset_label="synthetic_lab")
    proposal = propose(
        reconstruction,
        "recommend_analyst_investigation",
        authorized=True,
        in_scope=True,
        human_approved=False,
    )
    result = verify_proposal(proposal)
    assert result.solver_result == "sat"
    assert result.status == "verified_under_model"


def test_neural_holdout_is_labelled_synthetic() -> None:
    report = evaluate_neural_holdout()
    assert report.dataset == "synthetic_lab_features_v1"
    assert 0 <= report.f1 <= 1
    assert "synthetic" in report.notes.lower()
