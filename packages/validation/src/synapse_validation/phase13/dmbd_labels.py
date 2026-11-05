"""Inspect official DMBD pandas-style label JSON. Not process trees."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from synapse_validation.phase13.acquisition import sha256_file


def _as_int_year(value: object) -> str:
    if value is None:
        return "null"
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return "unparsed"


def inspect_label_file(path: Path) -> dict[str, object]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not {"experiment", "label"} <= set(payload):
        raise ValueError("expected pandas-orient JSON with experiment and label")
    experiments = payload["experiment"]
    labels = payload["label"]
    years = payload.get("year", {})
    n = len(experiments)
    if len(labels) != n:
        raise ValueError("experiment/label length mismatch")
    sample_ids = list(experiments.values())
    label_values = [str(labels[key]).lower() for key in experiments]
    year_values = [_as_int_year(years.get(key)) for key in experiments] if years else []
    return {
        "path": path.name,
        "sha256": sha256_file(path),
        "file_size_bytes": path.stat().st_size,
        "format": "pandas_orient_columns_experiment_year_label",
        "sample_count": n,
        "unique_sample_ids": len(set(sample_ids)),
        "label_counts": dict(Counter(label_values)),
        "year_counts": dict(Counter(year_values)),
        "label_scope": "sample",
        "label_source": "DMBD AV-consensus files as published on gdo168.llnl.gov",
        "id_prefix_sample": sample_ids[:3],
        "notes": (
            "These files label experiments/samples, not individual process events. "
            "They are not a substitute for trees_*.json process records."
        ),
    }


def experiment_ids(path: Path) -> set[str]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(value) for value in payload["experiment"].values()}


def compare_splits(
    train: dict[str, object],
    test: dict[str, object],
    *,
    train_ids: set[str] | None = None,
    test_ids: set[str] | None = None,
) -> dict[str, object]:
    overlap = 0
    if train_ids is not None and test_ids is not None:
        overlap = len(train_ids & test_ids)
    return {
        "train_samples": train["sample_count"],
        "test_samples": test["sample_count"],
        "documented_train": 40000,
        "documented_test": 25416,
        "train_matches_documented_count": train["sample_count"] == 40000,
        "test_matches_documented_count": test["sample_count"] == 25416,
        "train_test_id_overlap": overlap,
        "notes": (
            "Overview claimed 25,416 test samples. Verified unique IDs come from the "
            "inspected files. Train/test overlap must be zero for a valid split."
        ),
    }
