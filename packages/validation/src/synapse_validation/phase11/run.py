"""Phase 11 runner. Missing CIC-IDS2017 is a hard failure for external mode."""

from __future__ import annotations

import json
import os
import platform
import resource
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from synapse_validation.phase11 import EXPERIMENT_ID, PHASE11_VERSION
from synapse_validation.phase11.flow_explanations import evaluate_explanations, negative_cases
from synapse_validation.phase11.flow_loader import absent_manifest, load_flow_csv
from synapse_validation.phase11.flow_metrics import (
    balanced_accuracy,
    is_attack,
    macro_f1,
    per_class_scores,
    summarize_binary,
    weighted_f1,
)
from synapse_validation.phase11.flow_models import fit_models, predict_all
from synapse_validation.phase11.flow_splits import split_records
from synapse_validation.phase11.robustness import run_robustness

ROOT = Path(__file__).resolve().parents[5]
PHASE10_JSON = ROOT / "docs" / "research" / "generated" / "last-run.json"


def _env() -> dict[str, object]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "sklearn": __import__("sklearn").__version__,
    }


def _rss_kb() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _phase10_preserved() -> dict[str, object]:
    if not PHASE10_JSON.is_file():
        return {"available": False, "notes": "Phase 10 JSON not found beside this checkout."}
    payload = json.loads(PHASE10_JSON.read_text(encoding="utf-8"))
    acc = {
        item["experiment_id"]: item["multiclass_accuracy"]
        for item in payload.get("experiments", [])
    }
    return {
        "available": True,
        "experiment_id": payload.get("experiment_id"),
        "dataset": payload.get("dataset_name"),
        "dataset_class": "synthetic_lab",
        "findings_must_not_be_rewritten": [
            "Correlation, symbolic and hybrid three-class accuracy matched on 12 fixtures.",
            "Hybrid did not outperform simpler approaches on that synthetic set.",
            "Isolation Forest failed unusual-volume reconstructions (F1 0.0).",
            "Prediction equalled persistence.",
            "CIC-IDS2017 was not evaluated in Phase 10.",
        ],
        "three_class_accuracy": acc,
        "neural_holdout_f1": payload.get("neural_holdout_synthetic_features", {}).get("f1"),
        "prediction_advantage": payload.get("prediction", {}).get(
            "measurable_advantage_over_persistence"
        ),
        "cicids_available_in_phase10": payload.get("cicids2017", {}).get("available"),
    }


def _blocked(reason: str) -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "phase11_version": PHASE11_VERSION,
        "cicids2017_evaluated": False,
        "evaluated": False,
        "mode": "external",
        "blocker": reason,
        "manifest": absent_manifest(reason).as_dict(),
        "models": [],
        "phase10_preserved_findings": _phase10_preserved(),
        "capability_matrix": capability_matrix(),
        "notes": (
            "No CIC-IDS2017 metrics were generated. Synthetic fixtures were not "
            "substituted for the missing corpus."
        ),
        "software": _env(),
        "started_at": datetime.now(UTC).isoformat(),
        "ended_at": datetime.now(UTC).isoformat(),
    }


def capability_matrix() -> list[dict[str, str]]:
    return [
        {
            "capability": "Flow classification",
            "cicids2017": "Evaluate when files are present",
            "linux_agent_lab": "Not applicable",
            "synthetic_fixtures": "Controlled protocol tests",
        },
        {
            "capability": "Process lifecycle",
            "cicids2017": "Not available",
            "linux_agent_lab": "Evaluate",
            "synthetic_fixtures": "Controlled tests (Phase 10)",
        },
        {
            "capability": "PID reuse",
            "cicids2017": "Not available",
            "linux_agent_lab": "Evaluate",
            "synthetic_fixtures": "Controlled tests (Phase 10)",
        },
        {
            "capability": "Process-network attribution",
            "cicids2017": "Not available",
            "linux_agent_lab": "Evaluate",
            "synthetic_fixtures": "Controlled tests (Phase 10)",
        },
        {
            "capability": "Flow explanation",
            "cicids2017": "Evaluate when files are present",
            "linux_agent_lab": "Only if flow evidence exists",
            "synthetic_fixtures": "Controlled tests",
        },
        {
            "capability": "Endpoint reconstruction",
            "cicids2017": "Not available directly",
            "linux_agent_lab": "Evaluate",
            "synthetic_fixtures": "Controlled tests (Phase 10)",
        },
        {
            "capability": "Agent identity / Ed25519",
            "cicids2017": "Not available",
            "linux_agent_lab": "Evaluate",
            "synthetic_fixtures": "Not a substitute for enrollment",
        },
        {
            "capability": "Phase 9 hybrid on flows",
            "cicids2017": "Not comparable",
            "linux_agent_lab": "Evaluate on reconstructions",
            "synthetic_fixtures": "Phase 10 synthetic reconstructions",
        },
        {
            "capability": "Z3 policy checks",
            "cicids2017": "Not a dataset metric",
            "linux_agent_lab": "Policy tests",
            "synthetic_fixtures": "Policy tests",
        },
    ]


def _score_models(models, test_records, truth_attack, truth_category) -> list[dict[str, object]]:
    predicted = predict_all(models, test_records)
    rows = []
    for name, bundle in predicted.items():
        binary = summarize_binary(truth_attack, bundle["pred"], bundle["scores"])
        pred_labels = tuple(
            "benchmark_attack_labelled_flow" if flag else "benchmark_benign_flow"
            for flag in bundle["pred"]
        )
        per_class = per_class_scores(truth_category, pred_labels)
        rows.append(
            {
                "model_id": name,
                "comparable_to_phase9_hybrid": False,
                "binary": binary,
                "per_class": per_class,
                "macro_f1": macro_f1(per_class),
                "weighted_f1": weighted_f1(per_class),
                "balanced_accuracy": balanced_accuracy(truth_category, pred_labels),
                "notes": models.notes[name if name != "flow_union" else "flow_union"],
            }
        )
    rows.append(
        {
            "model_id": "phase9_hybrid",
            "comparable_to_phase9_hybrid": False,
            "status": "not_comparable",
            "reason": models.notes["phase9_hybrid"],
        }
    )
    return rows, predicted["volume_rule"]["pred"]


def run_on_records(loaded, *, dataset_class: str) -> dict[str, object]:
    started = datetime.now(UTC)
    rss_before = _rss_kb()
    split, train_idx, val_idx, test_idx = split_records(loaded.records)
    train = [loaded.records[i] for i in train_idx]
    validation = [loaded.records[i] for i in val_idx]
    test = [loaded.records[i] for i in test_idx]
    fit_started = time.perf_counter()
    models = fit_models(train, validation)
    fit_seconds = time.perf_counter() - fit_started
    infer_started = time.perf_counter()
    truth_attack = tuple(is_attack(item.category) for item in test)
    truth_category = tuple(item.category for item in test)
    model_rows, rule_pred = _score_models(models, test, truth_attack, truth_category)
    infer_seconds = time.perf_counter() - infer_started
    explanations = evaluate_explanations(test, rule_pred, models)
    return {
        "experiment_id": EXPERIMENT_ID,
        "phase11_version": PHASE11_VERSION,
        "cicids2017_evaluated": dataset_class == "external_flow_benchmark",
        "evaluated": True,
        "dataset_class": dataset_class,
        "mode": dataset_class,
        "blocker": None,
        "manifest": loaded.manifest.as_dict(),
        "excluded": [
            {"source_row_id": item.source_row_id, "reason": item.reason} for item in loaded.excluded
        ],
        "split": split.as_dict(),
        "natural_class_distribution": loaded.manifest.label_counts,
        "resampling": "none; test set is unmodified",
        "preprocessing": {
            "medians_fitted_on": "train",
            "thresholds_fitted_on": "train benign (volume) and validation (forest F1)",
            "test_labels_used_for_fitting": False,
        },
        "models": model_rows,
        "explanations": explanations,
        "explanation_negative_tests": negative_cases(models),
        "robustness": run_robustness(test, models),
        "performance": {
            "fit_seconds": round(fit_seconds, 6),
            "inference_seconds": round(infer_seconds, 6),
            "rows_train": len(train),
            "rows_validation": len(validation),
            "rows_test": len(test),
            "rss_before_kb": rss_before,
            "rss_max_kb": _rss_kb(),
            "per_test_record_seconds": round(infer_seconds / max(len(test), 1), 6),
        },
        "phase10_preserved_findings": _phase10_preserved(),
        "capability_matrix": capability_matrix(),
        "software": _env(),
        "started_at": started.isoformat(),
        "ended_at": datetime.now(UTC).isoformat(),
        "limitations": [
            "Flow metrics are not Linux endpoint detection rates.",
            "Phase 9 hybrid remains not comparable on CIC-IDS2017 flows.",
            "A bounded sample is not the full CIC-IDS2017 corpus.",
            "Bootstrap intervals are descriptive, not hypothesis tests.",
        ],
    }


def resolve_external_path() -> Path | None:
    raw = os.environ.get("SYNAPSE_CICIDS_CSV", "").strip()
    if not raw:
        return None
    return Path(raw)


def run_phase11(*, mode: str = "external", csv_path: Path | None = None) -> dict[str, object]:
    if mode == "synthetic_protocol":
        if csv_path is None:
            raise ValueError("synthetic_protocol requires csv_path")
        loaded = load_flow_csv(csv_path, dataset_class="synthetic_flow_protocol")
        return run_on_records(loaded, dataset_class="synthetic_flow_protocol")
    path = csv_path or resolve_external_path()
    if path is None:
        return _blocked(
            "CIC-IDS2017 is not present. Set SYNAPSE_CICIDS_CSV to a local CSV. "
            "This command does not download the corpus and does not fall back to fixtures."
        )
    loaded = load_flow_csv(path, dataset_class="external_flow_benchmark")
    return run_on_records(loaded, dataset_class="external_flow_benchmark")
