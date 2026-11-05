"""Phase 13 runner. Missing process evidence fails closed. Labels are not trees."""

from __future__ import annotations

import json
import os
import platform
import resource
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from synapse_validation import FEATURE_SCHEMA as PHASE10_FEATURE_SCHEMA
from synapse_validation.phase12.loader import absent_manifest, load_endpoint_jsonl
from synapse_validation.phase12.splits import split_samples
from synapse_validation.phase13 import EXPERIMENT_ID, FEATURE_SCHEMA, PHASE13_VERSION
from synapse_validation.phase13.candidates import VERIFIED_DMBD, discovery_payload
from synapse_validation.phase13.dmbd_labels import (
    compare_splits,
    experiment_ids,
    inspect_label_file,
)
from synapse_validation.phase13.explanations import evaluate_explanations
from synapse_validation.phase13.features import FEATURE_DEFINITIONS, extract_sample_features
from synapse_validation.phase13.inspect import inspect_jsonl
from synapse_validation.phase13.policy import verify_claim_policy
from synapse_validation.phase13.reasoning import evaluate as evaluate_detection
from synapse_validation.phase13.reasoning import fit_thresholds, labels_by_sample
from synapse_validation.phase13.reconstruction import annotate
from synapse_validation.phase13.robustness import run_robustness

ROOT = Path(__file__).resolve().parents[5]
PHASE10_JSON = ROOT / "docs" / "research" / "generated" / "last-run.json"
PHASE11_JSON = ROOT / "docs" / "research" / "generated" / "phase11-last-run.json"
PHASE12_JSON = ROOT / "docs" / "research" / "generated" / "phase12-last-run.json"


def _rss_kb() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _preserve(path: Path, name: str) -> dict[str, object]:
    if not path.is_file():
        return {"available": False, "name": name}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "available": True,
        "name": name,
        "experiment_id": payload.get("experiment_id"),
        "must_not_rewrite": True,
    }


def resolve_labels_dir() -> Path | None:
    raw = os.environ.get("SYNAPSE_DMBD_LABELS_DIR", "").strip()
    if raw:
        path = Path(raw)
        return path if path.is_dir() else None
    fallback = Path("/tmp/synapse-dmbd")
    train = fallback / "truth_labels_train.json"
    test = fallback / "truth_labels_test.json"
    if train.is_file() and test.is_file():
        return fallback
    return None


def inspect_dmbd_labels(directory: Path | None) -> dict[str, object]:
    if directory is None:
        return {"available": False, "reason": "no label directory configured or present"}
    train_path = directory / "truth_labels_train.json"
    test_path = directory / "truth_labels_test.json"
    if not train_path.is_file() or not test_path.is_file():
        return {
            "available": False,
            "reason": "truth_labels_train.json or truth_labels_test.json missing",
            "directory": directory.name,
        }
    train = inspect_label_file(train_path)
    test = inspect_label_file(test_path)
    ids_train = experiment_ids(train_path)
    ids_test = experiment_ids(test_path)
    comparison = compare_splits(train, test, train_ids=ids_train, test_ids=ids_test)
    return {
        "available": True,
        "directory": directory.name,
        "train": train,
        "test": test,
        "split_comparison": comparison,
        "not_process_trees": True,
        "independent_process_evaluation": False,
        "notes": (
            "Official DMBD sample labels were inspected. trees_*.json were not loaded. "
            "This is not independent endpoint reconstruction or detection."
        ),
    }


def resolve_external_path() -> Path | None:
    for key in ("SYNAPSE_DMBD_JSONL", "SYNAPSE_ENDPOINT_DATASET_PATH"):
        raw = os.environ.get(key, "").strip()
        if raw:
            return Path(raw)
    return None


def _software() -> dict[str, object]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "sklearn": __import__("sklearn").__version__,
        "phase13_version": PHASE13_VERSION,
        "phase10_feature_schema": PHASE10_FEATURE_SCHEMA,
        "sample_feature_schema": FEATURE_SCHEMA,
    }


def _common(blocker: str | None) -> dict[str, object]:
    labels = inspect_dmbd_labels(resolve_labels_dir())
    return {
        "experiment_id": EXPERIMENT_ID,
        "phase13_version": PHASE13_VERSION,
        "feature_schema": FEATURE_SCHEMA,
        "dmbd_process_trees_evaluated": False,
        "dmbd_labels_inspected": bool(labels.get("available")),
        "winmet_evaluated": False,
        "optc_evaluated": False,
        "independent_endpoint_validation_completed": False,
        "scientific_completion": False,
        "blocker": blocker,
        "discovery": discovery_payload(),
        "verified_dmbd_http": VERIFIED_DMBD,
        "dmbd_labels": labels,
        "feature_definitions": list(FEATURE_DEFINITIONS),
        "phase10_preserved": _preserve(PHASE10_JSON, "phase10"),
        "phase11_preserved": _preserve(PHASE11_JSON, "phase11"),
        "phase12_preserved": _preserve(PHASE12_JSON, "phase12"),
        "software": _software(),
        "acquisition_bound_bytes": 8 * 1024 * 1024,
    }


def blocked(reason: str) -> dict[str, object]:
    payload = _common(reason)
    payload.update(
        {
            "evaluated": False,
            "mode": "external",
            "dataset_class": None,
            "manifest": absent_manifest(reason).as_dict(),
            "notes": (
                "No DMBD/WinMET/OpTC process evidence was evaluated. "
                "Label-file inspection is not reconstruction. "
                "Synthetic fixtures were not substituted."
            ),
            "started_at": datetime.now(UTC).isoformat(),
            "ended_at": datetime.now(UTC).isoformat(),
        }
    )
    return payload


def run_on_records(loaded, *, dataset_class: str) -> dict[str, object]:
    started = datetime.now(UTC)
    rss_before = _rss_kb()
    rec_started = time.perf_counter()
    reconstruction = annotate(loaded.records)
    rec_seconds = time.perf_counter() - rec_started
    nodes = reconstruction["base"].nodes
    feat_started = time.perf_counter()
    features = extract_sample_features(loaded.records, nodes)
    feat_seconds = time.perf_counter() - feat_started
    split = split_samples(loaded.records)
    grouped = labels_by_sample(loaded.records)
    det_started = time.perf_counter()
    detection = evaluate_detection(features, grouped, split)
    det_seconds = time.perf_counter() - det_started
    train_rows = [features[sid] for sid in split.train_samples if sid in features]
    train_labels = [grouped.get(sid, "unknown") for sid in split.train_samples if sid in features]
    thresholds = fit_thresholds(train_rows, train_labels)
    explanations = evaluate_explanations(loaded.records, nodes, features, thresholds)
    policy = {
        "empty_malicious_claim": verify_claim_policy(
            insufficient_evidence=True,
            claim_malicious=True,
            has_source_records=False,
        ),
        "grounded_benign": verify_claim_policy(
            insufficient_evidence=False,
            claim_malicious=False,
            has_source_records=True,
        ),
    }
    independent = dataset_class == "external_endpoint_benchmark"
    payload = _common(None)
    payload.update(
        {
            "evaluated": True,
            "mode": dataset_class,
            "dataset_class": dataset_class,
            "dmbd_process_trees_evaluated": independent,
            "independent_endpoint_validation_completed": independent,
            "scientific_completion": independent,
            "manifest": loaded.manifest.as_dict(),
            "inspection": inspect_jsonl(Path(loaded.manifest.path)),
            "excluded": [
                {"source_record_id": item.source_record_id, "reason": item.reason}
                for item in loaded.excluded
            ],
            "split": split.as_dict(),
            "reconstruction": {
                key: reconstruction[key] for key in reconstruction if key not in {"nodes", "base"}
            },
            "detection": detection,
            "explanations": explanations,
            "policy_z3": policy,
            "robustness": run_robustness(loaded.records),
            "performance": {
                "reconstruction_seconds": round(rec_seconds, 6),
                "feature_seconds": round(feat_seconds, 6),
                "detection_seconds": round(det_seconds, 6),
                "rss_before_kb": rss_before,
                "rss_max_kb": _rss_kb(),
                "rows": loaded.manifest.row_count,
                "samples": loaded.manifest.sample_count,
            },
            "limitations": [
                "Sample labels are not event-level ground truth.",
                "Phase 9 hybrid is not comparable on Wintap/DMBD identities.",
                "Relationship labels are not calibrated probabilities.",
                "Z3 SAT is not real-world safety.",
                loaded.manifest.notes,
            ],
            "notes": loaded.manifest.notes,
            "started_at": started.isoformat(),
            "ended_at": datetime.now(UTC).isoformat(),
        }
    )
    if dataset_class == "synthetic_endpoint_protocol":
        payload["scientific_completion"] = False
        payload["independent_endpoint_validation_completed"] = False
        payload["dmbd_process_trees_evaluated"] = False
        payload["blocker"] = None
        payload["notes"] = (
            "SYNTHETIC PROTOCOL ONLY. Not DMBD, WinMET, or OpTC. "
            "Not independent scientific validation."
        )
    return payload


def run_phase13(*, mode: str = "external", jsonl_path: Path | None = None) -> dict[str, object]:
    if mode == "synthetic_protocol":
        if jsonl_path is None:
            raise ValueError("synthetic_protocol requires jsonl_path")
        loaded = load_endpoint_jsonl(jsonl_path, dataset_class="synthetic_endpoint_protocol")
        return run_on_records(loaded, dataset_class="synthetic_endpoint_protocol")
    path = jsonl_path or resolve_external_path()
    if path is None:
        return blocked(
            "No independent endpoint process dataset is present. Set SYNAPSE_DMBD_JSONL "
            "to local DMBD-like process JSONL. trees_*.json were not auto-downloaded "
            "(≈1 GB/shard). Label JSON inspection, if present, is not tree evaluation."
        )
    loaded = load_endpoint_jsonl(path, dataset_class="external_endpoint_benchmark")
    return run_on_records(loaded, dataset_class="external_endpoint_benchmark")
