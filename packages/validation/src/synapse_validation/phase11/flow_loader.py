"""Bounded flow CSV loader. Never fabricates Linux process events."""

from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from synapse_validation.datasets.cicids2017 import map_label as _phase10_map_label
from synapse_validation.phase11.provenance import (
    CITATION,
    EXCLUSIONS,
    IDENTIFIER_OR_LEAK_FIELDS,
    KNOWN_LIMITATIONS,
    LICENSE_NOTES,
    NUMERIC_CANDIDATES,
    OFFICIAL_SOURCE,
    UNAVAILABLE_UNTIL_FILES_INSPECTED,
)

MAX_BYTES = 32 * 1024 * 1024
MAX_ROWS = 20000
MAX_COLUMNS = 120
MAX_FIELD = 4096
REQUIRED = (
    "Destination Port",
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Label",
)

KNOWN_ATTACK_LABELS = {
    "PortScan",
    "DoS Hulk",
    "DDoS",
    "DoS GoldenEye",
    "DoS slowloris",
    "DoS Slowhttptest",
    "FTP-Patator",
    "SSH-Patator",
    "Bot",
    "Infiltration",
    "Heartbleed",
    "Web Attack – Brute Force",
    "Web Attack – XSS",
    "Web Attack – Sql Injection",
}


def flow_category(raw: str) -> str:
    base = _phase10_map_label(raw)
    if base != "benchmark_attack_labelled_flow":
        return base
    if raw.strip() in KNOWN_ATTACK_LABELS:
        return "benchmark_attack_labelled_flow"
    return "benchmark_unsupported_label"


def _normalize_header(name: str) -> str:
    return " ".join(name.strip().lstrip("\ufeff").split())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def parse_numeric(raw: str) -> float | None:
    text = raw.strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in {"nan", "infinity", "+infinity", "-infinity", "inf", "+inf", "-inf"}:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    return value


@dataclass(frozen=True)
class FlowRecord:
    source_row_id: str
    source_file: str
    line_number: int
    fields: dict[str, str]
    numbers: dict[str, float]
    original_label: str
    category: str
    timestamp_raw: str


@dataclass(frozen=True)
class ExcludedRow:
    source_row_id: str
    reason: str


@dataclass
class FlowManifest:
    name: str
    version: str
    source: str
    citation: str
    license_notes: str
    path: str
    sha256: str
    file_size_bytes: int
    row_count: int
    excluded_count: int
    excluded_reasons: dict[str, int]
    columns: list[str]
    numeric_columns: list[str]
    label_column: str
    label_counts: dict[str, int]
    category_counts: dict[str, int]
    missing_value_counts: dict[str, int]
    duplicate_record_count: int
    timestamp_min: str | None
    timestamp_max: str | None
    feature_exclusions: dict[str, str]
    known_limitations: tuple[str, ...]
    unavailable_until_inspected: tuple[str, ...]
    processing: dict[str, object]
    available: bool
    dataset_class: str
    notes: str
    verified: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["known_limitations"] = list(self.known_limitations)
        payload["unavailable_until_inspected"] = list(self.unavailable_until_inspected)
        return payload


@dataclass(frozen=True)
class LoadedFlows:
    records: tuple[FlowRecord, ...]
    excluded: tuple[ExcludedRow, ...]
    manifest: FlowManifest


def _assert_safe_file(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    if "\x00" in str(path):
        raise ValueError("invalid path")
    return resolved


def load_flow_csv(
    path: Path,
    *,
    dataset_class: str,
    max_rows: int = MAX_ROWS,
    max_bytes: int = MAX_BYTES,
) -> LoadedFlows:
    resolved = _assert_safe_file(path)
    size = resolved.stat().st_size
    if size > max_bytes:
        raise ValueError(f"CSV exceeds max_bytes={max_bytes}")
    checksum = file_sha256(resolved)
    excluded: list[ExcludedRow] = []
    records: list[FlowRecord] = []
    labels: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    signatures: Counter[tuple[tuple[str, str], ...]] = Counter()
    timestamps: list[str] = []
    with resolved.open("r", encoding="utf-8", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        headers = [_normalize_header(name) for name in reader.fieldnames]
        if len(headers) > MAX_COLUMNS:
            raise ValueError("too many columns")
        if len(headers) != len(set(headers)):
            raise ValueError("duplicate column names")
        rename = dict(zip(reader.fieldnames, headers, strict=True))
        missing_cols = [column for column in REQUIRED if column not in headers]
        if missing_cols:
            raise ValueError(f"missing columns: {missing_cols}")
        numeric_cols = [column for column in headers if column in NUMERIC_CANDIDATES]
        for index, raw in enumerate(reader, start=2):
            source_row_id = f"{resolved.name}:{index}"
            if len(records) >= max_rows:
                excluded.append(ExcludedRow(source_row_id, "max_rows"))
                continue
            row = {
                _normalize_header(rename[key]): (value or "").strip() for key, value in raw.items()
            }
            if any(len(value) > MAX_FIELD for value in row.values()):
                excluded.append(ExcludedRow(source_row_id, "field_too_long"))
                continue
            if not any(row.values()):
                excluded.append(ExcludedRow(source_row_id, "empty_row"))
                continue
            label = row.get("Label", "")
            if not label:
                excluded.append(ExcludedRow(source_row_id, "missing_label"))
                continue
            numbers: dict[str, float] = {}
            malformed = False
            for column in numeric_cols:
                parsed = parse_numeric(row.get(column, ""))
                if parsed is None:
                    missing[column] += 1
                    if row.get(column, ""):
                        excluded.append(ExcludedRow(source_row_id, f"non_finite:{column}"))
                        malformed = True
                        break
                else:
                    numbers[column] = parsed
            if malformed:
                continue
            category = flow_category(label)
            signature = tuple(sorted((key, row[key]) for key in row if key != "Timestamp"))
            signatures[signature] += 1
            stamp = row.get("Timestamp", "")
            if stamp:
                timestamps.append(stamp)
            labels[label] += 1
            categories[category] += 1
            records.append(
                FlowRecord(
                    source_row_id=source_row_id,
                    source_file=resolved.name,
                    line_number=index,
                    fields=row,
                    numbers=numbers,
                    original_label=label,
                    category=category,
                    timestamp_raw=stamp,
                )
            )
    duplicate_count = sum(count - 1 for count in signatures.values() if count > 1)
    truncated = any(item.reason == "max_rows" for item in excluded)
    notes = "External or fixture flow records. Not enrolled-agent telemetry."
    if truncated:
        notes += " Load stopped at max_rows; this run is a bounded sample."
    if dataset_class == "synthetic_flow_protocol":
        notes += " SYNTHETIC PROTOCOL FIXTURE. Not CIC-IDS2017."
    manifest = FlowManifest(
        name="cicids2017_flow" if dataset_class == "external_flow_benchmark" else dataset_class,
        version="phase11-adapter-0.8.0",
        source=OFFICIAL_SOURCE if dataset_class == "external_flow_benchmark" else "test_fixture",
        citation=CITATION,
        license_notes=LICENSE_NOTES,
        path=str(resolved),
        sha256=checksum,
        file_size_bytes=size,
        row_count=len(records),
        excluded_count=len(excluded),
        excluded_reasons=dict(Counter(item.reason.split(":")[0] for item in excluded)),
        columns=headers,
        numeric_columns=numeric_cols,
        label_column="Label",
        label_counts=dict(labels),
        category_counts=dict(categories),
        missing_value_counts=dict(missing),
        duplicate_record_count=duplicate_count,
        timestamp_min=min(timestamps) if timestamps else None,
        timestamp_max=max(timestamps) if timestamps else None,
        feature_exclusions=dict(EXCLUSIONS),
        known_limitations=KNOWN_LIMITATIONS,
        unavailable_until_inspected=UNAVAILABLE_UNTIL_FILES_INSPECTED
        if dataset_class != "external_flow_benchmark"
        else (),
        processing={
            "max_rows": max_rows,
            "max_bytes": max_bytes,
            "non_finite_policy": "exclude_row",
            "identifier_fields_not_used_as_features": list(IDENTIFIER_OR_LEAK_FIELDS),
        },
        available=True,
        dataset_class=dataset_class,
        notes=notes,
        verified={
            "sha256": checksum,
            "file_size_bytes": size,
            "row_count": len(records),
            "columns": headers,
        },
    )
    return LoadedFlows(tuple(records), tuple(excluded), manifest)


def absent_manifest(reason: str) -> FlowManifest:
    return FlowManifest(
        name="cicids2017",
        version="not_present",
        source=OFFICIAL_SOURCE,
        citation=CITATION,
        license_notes=LICENSE_NOTES,
        path="",
        sha256="",
        file_size_bytes=0,
        row_count=0,
        excluded_count=0,
        excluded_reasons={},
        columns=[],
        numeric_columns=[],
        label_column="Label",
        label_counts={},
        category_counts={},
        missing_value_counts={},
        duplicate_record_count=0,
        timestamp_min=None,
        timestamp_max=None,
        feature_exclusions=dict(EXCLUSIONS),
        known_limitations=KNOWN_LIMITATIONS,
        unavailable_until_inspected=UNAVAILABLE_UNTIL_FILES_INSPECTED,
        processing={},
        available=False,
        dataset_class="external_flow_benchmark",
        notes=reason,
        verified={},
    )
