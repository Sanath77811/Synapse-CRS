"""Reproducible experiments A–E on synthetic labelled reconstructions."""

from __future__ import annotations

import os
import platform
import resource
import sys
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from synapse_reasoning import ENGINE_VERSION, FEATURE_VERSION, MODEL_ID, RULE_VERSION
from synapse_reasoning.evaluation import evaluate_neural_holdout
from synapse_reasoning.hybrid import assess

from synapse_validation import VALIDATION_VERSION
from synapse_validation.classifiers import (
    correlation_class,
    hybrid_class,
    hybrid_without_quality_class,
    neural_class,
    neural_symbolic_class,
    symbolic_class,
)
from synapse_validation.compatibility import COMPATIBILITY, compatibility_summary
from synapse_validation.counterfactuals import run_counterfactual_cases
from synapse_validation.datasets.cicids2017 import load_cicids_csv, unavailable_manifest
from synapse_validation.explainability import measure_explanation
from synapse_validation.metrics import binary_confusion, multiclass_accuracy
from synapse_validation.prediction_eval import run_prediction_eval
from synapse_validation.scenarios import labelled_scenarios, reconstruct_scenario
from synapse_validation.splits import DEFAULT_SPLIT, sequential_indices
from synapse_validation.verification_matrix import run_matrix

MODES: tuple[tuple[str, str, Callable], ...] = (
    ("A_deterministic_correlation", "Phase 8 findings mapped to three classes", correlation_class),
    ("B_neural_only", "Isolation Forest unusual vs not; cannot emit insufficient", neural_class),
    ("C_symbolic_only", "Symbolic rule supports with conservative ties", symbolic_class),
    ("D_hybrid", "Phase 9 hybrid selected hypothesis mapped to three classes", hybrid_class),
    (
        "E_neural_plus_symbolic",
        "Neural + symbolic without completeness gate",
        neural_symbolic_class,
    ),
    (
        "E_hybrid_without_evidence_quality",
        "Hybrid minus reconstruction-completeness H4 boost",
        hybrid_without_quality_class,
    ),
)


def _env() -> dict[str, object]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "sklearn": __import__("sklearn").__version__,
        "numpy": __import__("numpy").__version__,
    }


def _rss_kb() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _evaluate_mode(name: str, task: str, fn: Callable, reconstructions, truths) -> dict:
    start = time.perf_counter()
    preds = tuple(fn(item) for item in reconstructions)
    elapsed = time.perf_counter() - start
    y_true = tuple(label == "unusual_volume" for label in truths)
    y_pred = tuple(label == "unusual_volume" for label in preds)
    confusion = binary_confusion(y_true, y_pred)
    return {
        "experiment_id": name,
        "task": task,
        "ground_truth": (
            "synthetic scenario class: typical | unusual_volume | insufficient. "
            "unusual_volume is lab network volume, not malice."
        ),
        "dataset_class": "synthetic_lab",
        "predictions": list(preds),
        "truth": list(truths),
        "multiclass_accuracy": multiclass_accuracy(truths, preds),
        "unusual_volume_binary": {
            "true_positive": confusion.true_positive,
            "false_positive": confusion.false_positive,
            "true_negative": confusion.true_negative,
            "false_negative": confusion.false_negative,
            "precision": confusion.precision,
            "recall": confusion.recall,
            "f1": confusion.f1,
            "false_positive_rate": confusion.false_positive_rate,
            "accuracy": confusion.accuracy,
            "confusion_matrix": confusion.matrix,
        },
        "per_class": {
            label: {
                "support": truths.count(label),
                "correct": sum(
                    1
                    for truth, pred in zip(truths, preds, strict=True)
                    if truth == label and pred == label
                ),
            }
            for label in ("typical", "unusual_volume", "insufficient")
        },
        "elapsed_seconds": round(elapsed, 6),
        "throughput_scenarios_per_second": round(len(reconstructions) / max(elapsed, 1e-9), 4),
        "limitations": (
            "Outputs are not interchangeable attack verdicts. "
            "Neural-only cannot express insufficient evidence."
        ),
    }


def _cicids_section() -> dict[str, object]:
    env_path = os.environ.get("SYNAPSE_CICIDS_CSV", "").strip()
    if not env_path:
        manifest = unavailable_manifest(
            "CIC-IDS2017 is not in the repository. Set SYNAPSE_CICIDS_CSV to a local CSV."
        )
        return {
            "available": False,
            "manifest": manifest.as_dict(),
            "compatibility": compatibility_summary(),
            "directly_compatible_features": 0,
            "experiment": "not_run",
            "notes": "Do not treat missing CIC-IDS2017 as a silent skip of documentation.",
        }
    loaded = load_cicids_csv(Path(env_path))
    return {
        "available": True,
        "manifest": loaded.manifest.as_dict(),
        "excluded": [{"row": item.row_number, "reason": item.reason} for item in loaded.excluded],
        "compatibility": compatibility_summary(),
        "feature_map": [
            {
                "synapse_feature": item.synapse_feature,
                "cicids_fields": list(item.cicids_fields),
                "status": item.status,
                "assumption": item.assumption,
            }
            for item in COMPATIBILITY
        ],
        "experiment": "adapter_only",
        "notes": (
            "Flow rows are external benchmark observations. They were not inserted "
            "into telemetry_events and were not scored with synthetic_lab_features_v1."
        ),
    }


def run_all() -> dict[str, object]:
    started = datetime.now(UTC)
    rss_before = _rss_kb()
    scenarios = labelled_scenarios()
    reconstructions = []
    truths = []
    for row in scenarios:
        reconstruction, _ = reconstruct_scenario(row["observations"])  # type: ignore[arg-type]
        reconstructions.append(reconstruction)
        truths.append(row["truth"])
    indices = sequential_indices(len(scenarios), DEFAULT_SPLIT)
    experiments = [
        _evaluate_mode(name, task, fn, reconstructions, tuple(truths)) for name, task, fn in MODES
    ]
    neural_holdout = evaluate_neural_holdout()
    explain_rows = []
    for reconstruction in reconstructions:
        assessment = assess(reconstruction, window_seconds=300, fingerprint="explain")
        explain_rows.append(measure_explanation(reconstruction, assessment).as_dict())
    mean_coverage = sum(float(item["evidence_coverage"]) for item in explain_rows) / len(
        explain_rows
    )
    payload = {
        "experiment_id": "phase10-research-validation-v1",
        "validation_version": VALIDATION_VERSION,
        "started_at": started.isoformat(),
        "ended_at": datetime.now(UTC).isoformat(),
        "dataset_name": "synthetic_labelled_reconstructions_v1",
        "dataset_version": "0.7.0",
        "dataset_checksum": "constructed_in_process",
        "feature_schema_version": FEATURE_VERSION,
        "model_version": MODEL_ID,
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
        "random_seed": DEFAULT_SPLIT.seed,
        "split": {
            "strategy": DEFAULT_SPLIT.strategy,
            "seed": DEFAULT_SPLIT.seed,
            "train": indices[0],
            "validation": indices[1],
            "test": indices[2],
            "notes": (
                "Scenarios are independently constructed fixtures. Sequential split is "
                "recorded; reported A–E metrics use the full labelled fixture set because "
                "no model is fitted on these reconstructions."
            ),
        },
        "threshold_configuration": {
            "neural": "IsolationForest contamination=0.1, unusualness=-decision_function",
            "tuned_on_test": False,
        },
        "software": _env(),
        "dataset_size_scenarios": len(scenarios),
        "label_counts": dict(Counter(truths)),
        "experiments": experiments,
        "neural_holdout_synthetic_features": {
            "dataset": neural_holdout.dataset,
            "precision": neural_holdout.precision,
            "recall": neural_holdout.recall,
            "f1": neural_holdout.f1,
            "false_positive_rate": neural_holdout.false_positive_rate,
            "test_normal": neural_holdout.test_normal,
            "test_unusual": neural_holdout.test_unusual,
            "notes": neural_holdout.notes,
            "pr_auc": None,
            "roc_auc": None,
            "auc_notes": "AUC omitted: tiny synthetic holdout and binary scores only.",
        },
        "explainability": {
            "mean_evidence_coverage": round(mean_coverage, 4),
            "all_reference_valid": all(
                item["evidence_reference_validity"] == 1.0 for item in explain_rows
            ),
            "all_rules_traceable": all(item["rule_traceability"] == 1.0 for item in explain_rows),
            "unsupported_claim_total": sum(
                int(item["unsupported_claim_count"]) for item in explain_rows
            ),
            "per_scenario": explain_rows,
        },
        "counterfactuals": run_counterfactual_cases(),
        "formal_verification": run_matrix(),
        "prediction": run_prediction_eval(),
        "cicids2017": _cicids_section(),
        "performance": {
            "rss_max_kb": _rss_kb(),
            "rss_before_kb": rss_before,
            "elapsed_seconds": round((datetime.now(UTC) - started).total_seconds(), 4),
        },
        "known_limitations": [
            "Synthetic reconstructions are not enterprise detection performance.",
            "CIC-IDS2017 is not bundled and is not comparable to process-level features.",
            "Hybrid superiority is not assumed.",
            "SAT under Z3 is not real-world safety.",
            "Counterfactuals are feature ablation, not causal identification.",
        ],
    }
    return payload
