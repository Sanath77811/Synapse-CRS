"""Phase 13 tests. Fixtures and /tmp labels are not DMBD process-tree evaluation."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from synapse_validation.phase12.loader import load_endpoint_jsonl
from synapse_validation.phase13.acquisition import download_bounded, safe_extract_zip
from synapse_validation.phase13.dmbd_labels import inspect_label_file
from synapse_validation.phase13.features import extract_sample_features
from synapse_validation.phase13.policy import verify_claim_policy
from synapse_validation.phase13.reconstruction import annotate
from synapse_validation.phase13.run import run_phase13

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "validation"
    / "synthetic_endpoint_protocol.jsonl"
)
PHASE13 = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "validation"
    / "src"
    / "synapse_validation"
    / "phase13"
)


def test_fail_closed_without_process_jsonl() -> None:
    payload = run_phase13(mode="external", jsonl_path=None)
    assert payload["evaluated"] is False
    assert payload["scientific_completion"] is False
    assert payload["independent_endpoint_validation_completed"] is False
    assert payload["dmbd_process_trees_evaluated"] is False
    assert "not auto-downloaded" in payload["blocker"]
    assert payload["phase12_preserved"]["must_not_rewrite"] is True


def test_synthetic_protocol_is_not_independent_validation() -> None:
    payload = run_phase13(mode="synthetic_protocol", jsonl_path=FIXTURE)
    assert payload["evaluated"] is True
    assert payload["dataset_class"] == "synthetic_endpoint_protocol"
    assert payload["scientific_completion"] is False
    assert payload["dmbd_process_trees_evaluated"] is False
    assert "SYNTHETIC" in payload["notes"]
    assert payload["detection"]["phase9_hybrid"]["status"] == "not_comparable"
    assert payload["detection"]["completeness_aware"]["evaluation_unit"] == "sample"


def test_pid_hash_identity_and_pid_reuse() -> None:
    loaded = load_endpoint_jsonl(FIXTURE, dataset_class="synthetic_endpoint_protocol")
    report = annotate(loaded.records)
    assert report["pid_reuse_count"] >= 1
    s10 = [node for node in report["nodes"] if node.sample_id == "s10"]
    assert len({node.identity for node in s10}) == 2
    unsupported = [node for node in report["nodes"] if node.relationship == "unsupported"]
    assert unsupported
    confirmed = [node for node in report["nodes"] if node.relationship == "confirmed"]
    assert confirmed
    blob = json.dumps(report["relationship_counts"])
    assert "boot_id" not in blob


def test_features_exclude_labels() -> None:
    loaded = load_endpoint_jsonl(FIXTURE, dataset_class="synthetic_endpoint_protocol")
    report = annotate(loaded.records)
    rows = extract_sample_features(loaded.records, report["base"].nodes)
    for row in rows.values():
        assert "label" not in row.values
        assert "family" not in row.values


def test_sample_split_no_leakage() -> None:
    payload = run_phase13(mode="synthetic_protocol", jsonl_path=FIXTURE)
    split = payload["split"]
    train = set(split["train_samples"])
    test = set(split["test_samples"])
    assert train.isdisjoint(test)


def test_explanations_fail_closed_without_records() -> None:
    payload = run_phase13(mode="synthetic_protocol", jsonl_path=FIXTURE)
    assert payload["explanations"]["insufficient_empty_pass"] is True
    assert payload["explanations"]["valid_source_references"] is True


def test_z3_policy_unsat_on_unsupported_claim() -> None:
    bad = verify_claim_policy(
        insufficient_evidence=True,
        claim_malicious=True,
        has_source_records=False,
    )
    good = verify_claim_policy(
        insufficient_evidence=False,
        claim_malicious=False,
        has_source_records=True,
    )
    assert bad["result"] == "unsat"
    assert good["result"] == "sat"
    assert "not host safety" in good["notes"]


def test_zip_path_traversal_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("../escape.txt", "no")
    with pytest.raises(ValueError, match="unsafe zip"):
        safe_extract_zip(archive, tmp_path / "out")


def test_download_rejects_scheme_and_suffix(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="only http"):
        download_bounded("ftp://example.test/a.json", tmp_path / "a.json")
    with pytest.raises(ValueError, match="suffix"):
        download_bounded("https://example.test/a.exe", tmp_path / "a.exe")


def test_label_inspector_sample_scope(tmp_path: Path) -> None:
    path = tmp_path / "truth_labels_train.json"
    path.write_text(
        json.dumps(
            {
                "experiment": {"0": "E0", "1": "E1"},
                "year": {"0": 2017, "1": 2024},
                "label": {"0": "benign", "1": "malicious"},
            }
        ),
        encoding="utf-8",
    )
    inspected = inspect_label_file(path)
    assert inspected["sample_count"] == 2
    assert inspected["label_scope"] == "sample"
    assert inspected["label_counts"] == {"benign": 1, "malicious": 1}


def test_phase13_source_isolation() -> None:
    for path in PHASE13.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "import synapse_api" not in text
        assert "sqlalchemy" not in text
        assert "pickle" not in text
        assert "telemetry_events" not in text
