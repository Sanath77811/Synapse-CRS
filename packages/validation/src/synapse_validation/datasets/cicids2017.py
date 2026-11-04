"""Bounded CIC-IDS2017 CSV adapter.

The public CIC-IDS2017 corpus is not shipped in this repository. Operators
may point SYNAPSE_CICIDS_CSV at a local CSV. Parser fixtures are not the
full dataset.
"""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from synapse_validation.datasets.manifest import DatasetManifest

MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 5000
MAX_COLUMNS = 120
MAX_FIELD = 4096

CICIDS2017_COLUMNS: tuple[str, ...] = (
    "Destination Port",
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Label",
)

LABEL_MAP = {
    "BENIGN": "benchmark_benign_flow",
    "BENIGN ": "benchmark_benign_flow",
}


def map_label(raw: str) -> str:
    key = raw.strip()
    if key.upper() == "BENIGN":
        return "benchmark_benign_flow"
    if not key:
        return "benchmark_unlabelled"
    return "benchmark_attack_labelled_flow"


@dataclass(frozen=True)
class ExcludedRow:
    row_number: int
    reason: str


@dataclass(frozen=True)
class LoadedDataset:
    records: tuple[dict[str, str], ...]
    excluded: tuple[ExcludedRow, ...]
    manifest: DatasetManifest


def _normalize_header(name: str) -> str:
    return " ".join(name.strip().lstrip("\ufeff").split())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_cicids_csv(
    path: Path,
    *,
    max_rows: int = MAX_ROWS,
    max_bytes: int = MAX_BYTES,
    require_columns: tuple[str, ...] = CICIDS2017_COLUMNS,
) -> LoadedDataset:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    size = resolved.stat().st_size
    if size > max_bytes:
        raise ValueError(f"CSV exceeds max_bytes={max_bytes}")
    checksum = _sha256(resolved)
    excluded: list[ExcludedRow] = []
    records: list[dict[str, str]] = []
    labels: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    with resolved.open("r", encoding="utf-8", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        headers = [_normalize_header(name) for name in reader.fieldnames]
        if len(headers) > MAX_COLUMNS:
            raise ValueError("too many columns")
        rename = dict(zip(reader.fieldnames, headers, strict=True))
        missing = [column for column in require_columns if column not in headers]
        if missing:
            raise ValueError(f"missing columns: {missing}")
        for index, raw in enumerate(reader, start=2):
            if index - 1 > max_rows:
                excluded.append(ExcludedRow(index, "max_rows"))
                continue
            row = {
                _normalize_header(rename[key]): (value or "").strip() for key, value in raw.items()
            }
            if any(len(value) > MAX_FIELD for value in row.values()):
                excluded.append(ExcludedRow(index, "field_too_long"))
                continue
            if not any(row.values()):
                excluded.append(ExcludedRow(index, "empty_row"))
                continue
            label = row.get("Label", "")
            if not label:
                excluded.append(ExcludedRow(index, "missing_label"))
                continue
            category = map_label(label)
            labels[label] += 1
            categories[category] += 1
            records.append(row)
    manifest = DatasetManifest(
        name="cicids2017_csv",
        version="adapter-0.7.0",
        source="operator_supplied_csv",
        path=str(resolved),
        sha256=checksum,
        row_count=len(records),
        excluded_count=len(excluded),
        label_counts=dict(labels),
        category_counts=dict(categories),
        preprocessing={
            "strip_headers": True,
            "max_rows": max_rows,
            "max_bytes": max_bytes,
            "missing_value_policy": "keep_row_if_label_present",
        },
        available=True,
        notes="External flow records. Not enrolled-agent telemetry. Labels preserved.",
    )
    return LoadedDataset(tuple(records), tuple(excluded), manifest)


def unavailable_manifest(reason: str) -> DatasetManifest:
    return DatasetManifest(
        name="cicids2017",
        version="not_present",
        source="https://www.unb.ca/cic/datasets/ids-2017.html",
        path="",
        sha256="",
        row_count=0,
        excluded_count=0,
        label_counts={},
        category_counts={},
        preprocessing={},
        available=False,
        notes=reason,
    )
