"""Phase 12 runner. Missing DMBD is a hard failure for external mode."""

from __future__ import annotations

import json
import os
import platform
import resource
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from synapse_validation.phase12 import EXPERIMENT_ID, NORMALIZATION_VERSION, PHASE12_VERSION
from synapse_validation.phase12.candidates import CANDIDATES, PRIMARY_ADAPTER, suitability_matrix
from synapse_validation.phase12.detection import evaluate_sample_detection
from synapse_validation.phase12.explanations import evaluate_explanations
from synapse_validation.phase12.loader import absent_manifest, load_endpoint_jsonl
from synapse_validation.phase12.reconstruction import reconstruct
from synapse_validation.phase12.robustness import run_robustness
from synapse_validation.phase12.splits import split_samples

ROOT = Path(__file__).resolve().parents[5]
PHASE10_JSON = ROOT / "docs" / "research" / "generated" / "last-run.json"
PHASE11_JSON = ROOT / "docs" / "research" / "generated" / "phase11-last-run.json"


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


def _blocked(reason: str) -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "phase12_version": PHASE12_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "dmbd_evaluated": False,
        "winmet_evaluated": False,
        "optc_evaluated": False,
        "independent_endpoint_validation_completed": False,
        "evaluated": False,
        "mode": "external",
        "blocker": reason,
        "primary_adapter": PRIMARY_ADAPTER,
        "candidates": list(CANDIDATES),
        "suitability_matrix": suitability_matrix(),
        "manifest": absent_manifest(reason).as_dict(),
        "phase10_preserved": _preserve(PHASE10_JSON, "phase10"),
        "phase11_preserved": _preserve(PHASE11_JSON, "phase11"),
        "software": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "notes": (
            "No DMBD/WinMET/OpTC metrics were generated. Synthetic fixtures were "
            "not substituted for the missing corpora."
        ),
        "started_at": datetime.now(UTC).isoformat(),
        "ended_at": datetime.now(UTC).isoformat(),
    }


def run_on_records(loaded, *, dataset_class: str) -> dict[str, object]:
    started = datetime.now(UTC)
    rss_before = _rss_kb()
    load_note = loaded.manifest.notes
    rec_started = time.perf_counter()
    reconstruction = reconstruct(loaded.records)
    rec_seconds = time.perf_counter() - rec_started
    split = split_samples(loaded.records)
    det_started = time.perf_counter()
    detection = evaluate_sample_detection(loaded.records, split)
    det_seconds = time.perf_counter() - det_started
    explanations = evaluate_explanations(loaded.records, reconstruction.nodes)
    return {
        "experiment_id": EXPERIMENT_ID,
        "phase12_version": PHASE12_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "dmbd_evaluated": dataset_class == "external_endpoint_benchmark",
        "winmet_evaluated": False,
        "optc_evaluated": False,
        "independent_endpoint_validation_completed": dataset_class == "external_endpoint_benchmark",
        "evaluated": True,
        "dataset_class": dataset_class,
        "mode": dataset_class,
        "blocker": None,
        "primary_adapter": PRIMARY_ADAPTER,
        "candidates": list(CANDIDATES),
        "suitability_matrix": suitability_matrix(),
        "manifest": loaded.manifest.as_dict(),
        "excluded": [
            {"source_record_id": item.source_record_id, "reason": item.reason}
            for item in loaded.excluded
        ],
        "split": split.as_dict(),
        "reconstruction": {
            "process_count": reconstruction.process_count,
            "complete_lifecycle_count": reconstruction.complete_lifecycle_count,
            "orphan_count": reconstruction.orphan_count,
            "pid_reuse_count": reconstruction.pid_reuse_count,
            "missing_parent_count": reconstruction.missing_parent_count,
            "ordering_violations": reconstruction.ordering_violations,
            "coverage": reconstruction.coverage,
            "ambiguity_rate": reconstruction.ambiguity_rate,
            "notes": reconstruction.notes,
        },
        "detection": detection,
        "explanations": explanations,
        "robustness": run_robustness(loaded.records),
        "performance": {
            "reconstruction_seconds": round(rec_seconds, 6),
            "detection_seconds": round(det_seconds, 6),
            "rss_before_kb": rss_before,
            "rss_max_kb": _rss_kb(),
            "rows": loaded.manifest.row_count,
            "samples": loaded.manifest.sample_count,
        },
        "phase10_preserved": _preserve(PHASE10_JSON, "phase10"),
        "phase11_preserved": _preserve(PHASE11_JSON, "phase11"),
        "software": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "sklearn": __import__("sklearn").__version__,
        },
        "limitations": [
            "Sample labels are not event-level ground truth.",
            "Phase 9 hybrid is not comparable on Wintap/DMBD identities.",
            "Structural reconstruction metrics are not independent tree accuracy.",
            load_note,
        ],
        "started_at": started.isoformat(),
        "ended_at": datetime.now(UTC).isoformat(),
    }


def resolve_external_path() -> Path | None:
    for key in ("SYNAPSE_DMBD_JSONL", "SYNAPSE_ENDPOINT_DATASET_PATH"):
        raw = os.environ.get(key, "").strip()
        if raw:
            return Path(raw)
    return None


def run_phase12(*, mode: str = "external", jsonl_path: Path | None = None) -> dict[str, object]:
    if mode == "synthetic_protocol":
        if jsonl_path is None:
            raise ValueError("synthetic_protocol requires jsonl_path")
        loaded = load_endpoint_jsonl(jsonl_path, dataset_class="synthetic_endpoint_protocol")
        return run_on_records(loaded, dataset_class="synthetic_endpoint_protocol")
    path = jsonl_path or resolve_external_path()
    if path is None:
        return _blocked(
            "No independent endpoint dataset is present. Set SYNAPSE_DMBD_JSONL to a "
            "local JSONL of DMBD-like process rows. This command does not download "
            "DMBD, WinMET, or OpTC, and does not fall back to fixtures."
        )
    loaded = load_endpoint_jsonl(path, dataset_class="external_endpoint_benchmark")
    return run_on_records(loaded, dataset_class="external_endpoint_benchmark")
