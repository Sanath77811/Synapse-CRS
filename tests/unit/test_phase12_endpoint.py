"""Phase 12 endpoint protocol tests. Fixtures are not DMBD/WinMET/OpTC."""

import json
from pathlib import Path

import pytest
from synapse_validation.phase12.candidates import PRIMARY_ADAPTER, suitability_matrix
from synapse_validation.phase12.loader import file_sha256, load_endpoint_jsonl, normalize_row
from synapse_validation.phase12.reconstruction import reconstruct
from synapse_validation.phase12.run import run_phase12
from synapse_validation.phase12.splits import split_samples

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "validation"
    / "synthetic_endpoint_protocol.jsonl"
)
PHASE12 = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "validation"
    / "src"
    / "synapse_validation"
    / "phase12"
)


def test_absent_dataset_does_not_invent_metrics() -> None:
    payload = run_phase12(mode="external", jsonl_path=None)
    assert payload["dmbd_evaluated"] is False
    assert payload["independent_endpoint_validation_completed"] is False
    assert payload["evaluated"] is False
    assert "does not download" in payload["blocker"]
    assert payload["phase10_preserved"]["must_not_rewrite"] is True
    assert payload["primary_adapter"] == PRIMARY_ADAPTER


def test_synthetic_protocol_is_labelled_synthetic() -> None:
    payload = run_phase12(mode="synthetic_protocol", jsonl_path=FIXTURE)
    assert payload["evaluated"] is True
    assert payload["dmbd_evaluated"] is False
    assert payload["dataset_class"] == "synthetic_endpoint_protocol"
    assert "SYNTHETIC" in payload["manifest"]["notes"]
    hybrid = payload["detection"]["methods"]["phase9_hybrid"]
    assert hybrid["status"] == "not_comparable"
    assert payload["detection"]["label_scope"] == "sample"


def test_label_scope_and_unknown_labels() -> None:
    loaded = load_endpoint_jsonl(FIXTURE, dataset_class="synthetic_endpoint_protocol")
    assert any(item.reason == "unsupported_label_scope" for item in loaded.excluded)
    unknown = [item for item in loaded.records if item.label.value == "neverseenfam"]
    assert unknown
    assert unknown[0].label_scope == "sample"
    assert unknown[0].label.value != "benign"


def test_source_record_ids_preserved() -> None:
    loaded = load_endpoint_jsonl(FIXTURE, dataset_class="synthetic_endpoint_protocol")
    ids = {item.source_record_id for item in loaded.records}
    assert "r01" in ids
    assert loaded.manifest.sha256 == file_sha256(FIXTURE)


def test_pid_not_unique_and_reuse_detected() -> None:
    loaded = load_endpoint_jsonl(FIXTURE, dataset_class="synthetic_endpoint_protocol")
    report = reconstruct(loaded.records)
    assert report.pid_reuse_count >= 1
    s10 = [node for node in report.nodes if node.sample_id == "s10"]
    pids = {node.os_pid for node in s10}
    assert 50 in pids
    assert len({node.identity for node in s10}) == 2


def test_missing_parent_and_incomplete_lifecycle() -> None:
    loaded = load_endpoint_jsonl(FIXTURE, dataset_class="synthetic_endpoint_protocol")
    report = reconstruct(loaded.records)
    assert report.missing_parent_count >= 1
    incomplete = [node for node in report.nodes if not node.complete]
    assert incomplete


def test_split_is_sample_grouped() -> None:
    loaded = load_endpoint_jsonl(FIXTURE, dataset_class="synthetic_endpoint_protocol")
    split = split_samples(loaded.records)
    train = set(split.train_samples)
    val = set(split.validation_samples)
    test = set(split.test_samples)
    assert train.isdisjoint(val)
    assert train.isdisjoint(test)
    assert "s08" in split.test_samples
    assert "s01" in split.train_samples


def test_malformed_and_limits(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_bytes"):
        load_endpoint_jsonl(FIXTURE, dataset_class="synthetic_endpoint_protocol", max_bytes=10)
    loaded = load_endpoint_jsonl(FIXTURE, dataset_class="synthetic_endpoint_protocol")
    assert any(item.reason == "malformed_json" for item in loaded.excluded)


def test_does_not_fabricate_linux_identity() -> None:
    record = normalize_row(
        {
            "source_record_id": "x",
            "sample_id": "s",
            "event_type": "process",
            "os_pid": 8,
            "process_started": "t0",
        },
        source_file="f",
        dataset_class="synthetic_endpoint_protocol",
        version="t",
    )
    assert record.source_process_id.provenance == "derived"
    assert "boot" not in str(record.source_process_id.value)
    assert "start_ticks" not in str(record.source_process_id.value)


def test_explanations_and_reproducibility() -> None:
    first = run_phase12(mode="synthetic_protocol", jsonl_path=FIXTURE)
    second = run_phase12(mode="synthetic_protocol", jsonl_path=FIXTURE)
    assert first["reconstruction"]["process_count"] == second["reconstruction"]["process_count"]
    assert first["explanations"]["negative_tests"][0]["pass"]
    assert first["explanations"]["negative_tests"][1]["pass"]
    blob = json.dumps(first["explanations"]["sample"])
    assert "boot_id" not in blob
    assert first["explanations"]["sample"][0]["process_identity"] != "start_ticks"


def test_phase12_source_isolation() -> None:
    for path in PHASE12.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "import synapse_api" not in text
        assert "sqlalchemy" not in text
        assert "pickle" not in text


def test_suitability_matrix_does_not_claim_local_files() -> None:
    matrix = suitability_matrix()
    assert matrix
    joined = json.dumps(matrix)
    assert "files absent" in joined or "unavailable" in joined or "documented-unverified" in joined
