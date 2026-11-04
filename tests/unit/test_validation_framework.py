"""Phase 10 research validation: adapters, splits, metrics, experiments."""

import json
from pathlib import Path

import pytest
from synapse_reasoning.hybrid import assess
from synapse_validation.classifiers import (
    correlation_class,
    hybrid_class,
    neural_class,
    symbolic_class,
)
from synapse_validation.compatibility import compatibility_summary
from synapse_validation.counterfactuals import run_counterfactual_cases
from synapse_validation.datasets.cicids2017 import load_cicids_csv, map_label
from synapse_validation.experiments import run_all
from synapse_validation.explainability import fabricated_event_id_rejected, measure_explanation
from synapse_validation.metrics import binary_confusion, mae
from synapse_validation.report import render_markdown
from synapse_validation.scenarios import identity_gap, reconstruct_scenario, typical, unusual_volume
from synapse_validation.splits import assert_no_index_leakage, sequential_indices
from synapse_validation.verification_matrix import run_matrix

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "validation" / "cicids_parser_fixture.csv"
)


def test_cicids_adapter_reports_excluded_rows() -> None:
    loaded = load_cicids_csv(FIXTURE, max_rows=5000)
    assert loaded.manifest.available
    assert loaded.manifest.sha256
    assert loaded.excluded
    assert any(item.reason == "missing_label" for item in loaded.excluded)
    assert loaded.manifest.label_counts["BENIGN"] >= 1
    assert map_label("DoS Hulk") == "benchmark_attack_labelled_flow"
    assert map_label("BENIGN") == "benchmark_benign_flow"


def test_cicids_rejects_oversized_file(tmp_path: Path) -> None:
    path = tmp_path / "big.csv"
    path.write_bytes(b"x" * 100)
    with pytest.raises(ValueError, match="max_bytes"):
        load_cicids_csv(path, max_bytes=10)


def test_cicids_max_rows_is_reported() -> None:
    loaded = load_cicids_csv(FIXTURE, max_rows=2)
    assert loaded.manifest.row_count == 2
    assert any(item.reason == "max_rows" for item in loaded.excluded)


def test_cicids_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        load_cicids_csv(path)


def test_feature_compatibility_has_no_direct_maps() -> None:
    summary = compatibility_summary()
    assert summary.get("directly compatible", 0) == 0
    assert summary.get("directly_compatible", 0) == 0
    assert "not_available" in summary or "not_comparable" in summary


def test_label_mapping_preserves_attack_vs_benign() -> None:
    assert map_label("  BENIGN ") == "benchmark_benign_flow"
    assert map_label("") == "benchmark_unlabelled"


def test_split_has_no_leakage() -> None:
    train, validation, test = sequential_indices(12)
    assert_no_index_leakage(train, validation, test)
    assert train and validation and test


def test_metric_correctness() -> None:
    result = binary_confusion((True, True, False, False), (True, False, True, False))
    assert result.true_positive == 1
    assert result.false_negative == 1
    assert result.false_positive == 1
    assert result.true_negative == 1
    assert result.precision == 0.5
    assert mae((1.0, 3.0), (2.0, 3.0)) == 0.5


def test_classifiers_on_constructed_fixtures() -> None:
    typical_rec, _ = reconstruct_scenario(typical(10, 1))
    volume_rec, _ = reconstruct_scenario(unusual_volume(20, 9))
    gap_rec, _ = reconstruct_scenario(identity_gap(50, 3))
    assert correlation_class(typical_rec) == "typical"
    assert correlation_class(volume_rec) == "unusual_volume"
    assert correlation_class(gap_rec) == "insufficient"
    assert neural_class(gap_rec) == "typical"
    assert symbolic_class(gap_rec) == "insufficient"
    assert hybrid_class(gap_rec) == "insufficient"
    assert hybrid_class(typical_rec) == "typical"


def test_explainability_metrics() -> None:
    reconstruction, _ = reconstruct_scenario(identity_gap(50, 3))
    metrics = measure_explanation(reconstruction)
    assert metrics.evidence_reference_validity == 1.0
    assert metrics.rule_traceability == 1.0
    assert metrics.inferred_timeline_without_event_id
    assert fabricated_event_id_rejected(reconstruction)
    assessment = assess(reconstruction, window_seconds=300, fingerprint="x")
    observed = {item.event_id for item in reconstruction.observations}
    assert set(assessment.evidence_event_ids) <= observed
    inferred = [item for item in reconstruction.timeline if item.classification == "inferred"]
    assert inferred
    assert all(item.event_id is None for item in inferred)
    assert reconstruction.missing_evidence


def test_counterfactual_matrix() -> None:
    rows = {item["name"]: item for item in run_counterfactual_cases()}
    assert rows["remove_influential_network_volume"]["original_unchanged"]
    assert rows["repeat_same_scenario"]["reproducible"]
    assert rows["invalid_empty_reconstruction"]["rejected_or_empty"]


def test_z3_policy_matrix() -> None:
    rows = run_matrix()
    named = {item["name"]: item for item in rows}
    assert named["authorized_proposal"]["pass"]
    assert named["unauthorized_proposal"]["pass"]
    assert named["out_of_scope_target"]["pass"]
    assert named["unknown_target_identity"]["pass"]
    assert named["missing_evidence"]["pass"]
    assert named["missing_human_approval"]["pass"]
    assert named["destructive_action"]["pass"]
    assert named["forbidden_mitigation_type"]["pass"]
    assert named["invalid_executed_flag"]["pass"]
    assert named["conflicting_constraints"]["pass"]
    assert named["solver_timeout"]["pass"]


def test_reproducible_experiments_and_report() -> None:
    first = run_all()
    second = run_all()
    assert first["cicids2017"]["available"] is False
    assert first["prediction"]["measurable_advantage_over_persistence"] is False
    ids = [item["experiment_id"] for item in first["experiments"]]
    assert "A_deterministic_correlation" in ids
    assert "D_hybrid" in ids
    acc1 = {item["experiment_id"]: item["multiclass_accuracy"] for item in first["experiments"]}
    acc2 = {item["experiment_id"]: item["multiclass_accuracy"] for item in second["experiments"]}
    assert acc1 == acc2
    markdown = render_markdown(first)
    assert "## 1. Executive summary" in markdown
    assert "enterprise detection" in markdown.lower() or "not enterprise" in markdown.lower()
    json.dumps(first)


def test_no_pickle_in_validation() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "validation"
    for path in root.rglob("*.py"):
        if path.name == "isolation.py":
            continue
        text = path.read_text(encoding="utf-8")
        assert "pickle" not in text
