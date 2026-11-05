"""Phase 11 flow-benchmark protocol tests. Fixtures are not CIC-IDS2017."""

import json
from pathlib import Path

import pytest
from synapse_validation.metrics import binary_confusion
from synapse_validation.phase11.flow_loader import file_sha256, flow_category, load_flow_csv
from synapse_validation.phase11.flow_splits import split_records
from synapse_validation.phase11.isolation import assert_no_trust_boundary_crossing
from synapse_validation.phase11.report import render_markdown
from synapse_validation.phase11.run import run_phase11

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "validation" / "synthetic_flow_protocol.csv"
)
PHASE11_ROOT = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "validation"
    / "src"
    / "synapse_validation"
    / "phase11"
)


def test_absent_cicids_does_not_invent_metrics() -> None:
    payload = run_phase11(mode="external", csv_path=None)
    assert payload["cicids2017_evaluated"] is False
    assert payload["evaluated"] is False
    assert payload["models"] == []
    assert "Blocker" in payload["blocker"] or "not present" in payload["blocker"]
    assert payload["phase10_preserved_findings"]["available"] is True
    markdown = render_markdown(payload)
    assert "cicids2017_evaluated=False" in markdown


def test_synthetic_protocol_is_labelled_synthetic() -> None:
    payload = run_phase11(mode="synthetic_protocol", csv_path=FIXTURE)
    assert payload["evaluated"] is True
    assert payload["cicids2017_evaluated"] is False
    assert payload["dataset_class"] == "synthetic_flow_protocol"
    assert "SYNTHETIC" in payload["manifest"]["notes"]
    ids = [item["model_id"] for item in payload["models"]]
    assert "majority" in ids
    assert "volume_rule" in ids
    assert "isolation_forest" in ids
    assert "flow_union" in ids
    hybrid = next(item for item in payload["models"] if item["model_id"] == "phase9_hybrid")
    assert hybrid["status"] == "not_comparable"
    assert payload["preprocessing"]["test_labels_used_for_fitting"] is False


def test_split_reproducible_and_no_index_overlap() -> None:
    loaded = load_flow_csv(FIXTURE, dataset_class="synthetic_flow_protocol")
    first, *_ = split_records(loaded.records)
    second, *_ = split_records(loaded.records)
    assert first.train_ids == second.train_ids
    assert set(first.train_ids).isdisjoint(first.test_ids)
    assert set(first.train_ids).isdisjoint(first.validation_ids)


def test_file_hash_and_limits(tmp_path: Path) -> None:
    digest = file_sha256(FIXTURE)
    assert len(digest) == 64
    with pytest.raises(ValueError, match="max_bytes"):
        load_flow_csv(FIXTURE, dataset_class="synthetic_flow_protocol", max_bytes=10)
    loaded = load_flow_csv(FIXTURE, dataset_class="synthetic_flow_protocol", max_rows=3)
    assert loaded.manifest.row_count == 3
    assert any(item.reason == "max_rows" for item in loaded.excluded)


def test_malformed_and_missing_columns(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        load_flow_csv(bad, dataset_class="synthetic_flow_protocol")
    inf = load_flow_csv(FIXTURE, dataset_class="synthetic_flow_protocol")
    assert any(item.reason.startswith("non_finite") for item in inf.excluded)


def test_unknown_labels_not_mapped_to_benign() -> None:
    assert flow_category("NeverSeenXYZ") == "benchmark_unsupported_label"
    assert flow_category("BENIGN") == "benchmark_benign_flow"
    assert flow_category("PortScan") == "benchmark_attack_labelled_flow"
    loaded = load_flow_csv(FIXTURE, dataset_class="synthetic_flow_protocol")
    unsupported = [item for item in loaded.records if item.original_label == "NeverSeenXYZ"]
    assert unsupported
    assert unsupported[0].category != "benchmark_benign_flow"


def test_metric_imbalance_and_correctness() -> None:
    result = binary_confusion((True, False, False, False), (True, True, False, False))
    assert result.false_positive == 1
    assert result.true_positive == 1
    assert result.accuracy == 0.75


def test_explanations_cite_source_rows_not_processes() -> None:
    payload = run_phase11(mode="synthetic_protocol", csv_path=FIXTURE)
    assert payload["explanations"]["valid_source_references"] is True
    assert payload["explanations"]["reproducible"] is True
    negatives = {item["name"]: item for item in payload["explanation_negative_tests"]}
    assert negatives["missing_record_fields"]["pass"]
    assert negatives["process_claim_on_flow"]["pass"]
    sample = payload["explanations"]["sample"]
    if sample:
        assert "pid" not in json.dumps(sample).lower()
        assert "process" not in json.dumps(sample[0]["observed"]).lower()


def test_model_reproducibility() -> None:
    first = run_phase11(mode="synthetic_protocol", csv_path=FIXTURE)
    second = run_phase11(mode="synthetic_protocol", csv_path=FIXTURE)
    f1 = {item["model_id"]: item.get("binary", {}).get("f1") for item in first["models"]}
    f2 = {item["model_id"]: item.get("binary", {}).get("f1") for item in second["models"]}
    assert f1 == f2


def test_phase11_source_does_not_write_telemetry() -> None:
    for path in PHASE11_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if path.name == "isolation.py":
            continue
        assert_no_trust_boundary_crossing(text)
        assert "pickle" not in text
        assert "sqlalchemy" not in text
        assert "synapse_api" not in text


def test_duplicate_and_leakage_fields_recorded() -> None:
    loaded = load_flow_csv(FIXTURE, dataset_class="synthetic_flow_protocol")
    assert loaded.manifest.duplicate_record_count >= 1
    split, *_ = split_records(loaded.records)
    assert "duplicate_signature_leakage" in split.as_dict()
    assert "Timestamp" in loaded.manifest.feature_exclusions
