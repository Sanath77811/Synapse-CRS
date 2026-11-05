"""Bounded JSONL loader for DMBD-like process rows. No Linux identity fabrication."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from synapse_validation.phase12 import NORMALIZATION_VERSION
from synapse_validation.phase12.records import (
    EndpointRecord,
    derived,
    observed,
    unavailable,
)

MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 5000
MAX_FIELD = 4096
REQUIRED = ("source_record_id", "sample_id", "event_type")
KNOWN_SAMPLE_LABELS = {"benign", "malicious"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _text(raw: object) -> str:
    if raw is None:
        return ""
    return str(raw).strip()


def _field_optional(raw: object, *, numeric: bool = False):
    text = _text(raw)
    if not text:
        return unavailable()
    if numeric:
        try:
            return observed(int(text))
        except ValueError:
            try:
                return observed(float(text))
            except ValueError:
                return unavailable()
    return observed(text)


@dataclass(frozen=True)
class ExcludedRow:
    source_record_id: str
    reason: str


@dataclass
class EndpointManifest:
    name: str
    version: str
    path: str
    sha256: str
    file_size_bytes: int
    row_count: int
    excluded_count: int
    excluded_reasons: dict[str, int]
    sample_count: int
    label_counts: dict[str, int]
    label_scope: str
    split_counts: dict[str, int]
    event_types: dict[str, int]
    dataset_class: str
    available: bool
    notes: str
    normalization_version: str = NORMALIZATION_VERSION

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LoadedEndpoint:
    records: tuple[EndpointRecord, ...]
    excluded: tuple[ExcludedRow, ...]
    manifest: EndpointManifest


def _assert_file(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    if "\x00" in str(path):
        raise ValueError("invalid path")
    return resolved


def _label_fields(raw: dict[str, object]) -> tuple:
    label = _text(raw.get("label")).lower()
    scope = _text(raw.get("label_scope")) or "sample"
    source = _text(raw.get("label_source")) or "dataset"
    if not label:
        return unavailable(), "unknown", source, "missing_label"
    if scope != "sample":
        return observed(label), scope, source, "unsupported_label_scope"
    if label not in KNOWN_SAMPLE_LABELS and label not in {"", "unknown"}:
        return observed(label), "sample", source, "unknown_sample_label"
    return observed(label), "sample", source, ""


def normalize_row(
    raw: dict[str, object],
    *,
    source_file: str,
    dataset_class: str,
    version: str,
) -> EndpointRecord:
    sample_id = _text(raw.get("sample_id"))
    record_id = _text(raw.get("source_record_id"))
    pid_hash = _text(raw.get("pid_hash"))
    parent_hash = _text(raw.get("parent_pid_hash"))
    identity = observed(pid_hash) if pid_hash else unavailable()
    parent = observed(parent_hash) if parent_hash else unavailable()
    if not pid_hash and raw.get("os_pid") not in (None, ""):
        # Derived continuity key, not a Linux start_ticks or boot_id.
        start = _text(raw.get("process_started")) or _text(raw.get("event_timestamp"))
        identity = derived(f"os_pid:{raw.get('os_pid')}:start:{start or 'unknown'}")
    label, scope, label_source, _warning = _label_fields(raw)
    return EndpointRecord(
        source_dataset="dmbd" if dataset_class == "external_endpoint_benchmark" else dataset_class,
        source_dataset_version=version,
        source_file_id=source_file,
        source_record_id=record_id,
        source_sample_id=sample_id,
        source_host_id=_field_optional(raw.get("hostname") or raw.get("host_id")),
        source_process_id=identity,
        source_parent_process_id=parent,
        os_pid=_field_optional(raw.get("os_pid"), numeric=True),
        parent_os_pid=_field_optional(raw.get("parent_os_pid"), numeric=True),
        event_type=_text(raw.get("event_type")),
        event_timestamp=_field_optional(raw.get("event_timestamp") or raw.get("process_started")),
        process_start_timestamp=_field_optional(raw.get("process_started")),
        process_end_timestamp=_field_optional(raw.get("process_term")),
        network_connection_reference=_field_optional(raw.get("conn_id")),
        label=label,
        label_scope=scope,  # type: ignore[arg-type]
        label_source=label_source,
        split=_text(raw.get("split")) or "unspecified",
        raw={key: raw[key] for key in raw if len(_text(raw[key])) <= MAX_FIELD},
    )


def load_endpoint_jsonl(
    path: Path,
    *,
    dataset_class: str,
    max_rows: int = MAX_ROWS,
    max_bytes: int = MAX_BYTES,
) -> LoadedEndpoint:
    resolved = _assert_file(path)
    size = resolved.stat().st_size
    if size > max_bytes:
        raise ValueError(f"JSONL exceeds max_bytes={max_bytes}")
    checksum = file_sha256(resolved)
    records: list[EndpointRecord] = []
    excluded: list[ExcludedRow] = []
    labels: Counter[str] = Counter()
    splits: Counter[str] = Counter()
    types: Counter[str] = Counter()
    samples: set[str] = set()
    with resolved.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if len(records) >= max_rows:
                excluded.append(ExcludedRow(f"{resolved.name}:{line_number}", "max_rows"))
                continue
            text = line.strip()
            if not text:
                continue
            if len(text) > MAX_FIELD * 8:
                excluded.append(ExcludedRow(f"{resolved.name}:{line_number}", "line_too_long"))
                continue
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                excluded.append(ExcludedRow(f"{resolved.name}:{line_number}", "malformed_json"))
                continue
            if not isinstance(raw, dict):
                excluded.append(ExcludedRow(f"{resolved.name}:{line_number}", "not_an_object"))
                continue
            missing = [key for key in REQUIRED if not _text(raw.get(key))]
            if missing:
                excluded.append(
                    ExcludedRow(f"{resolved.name}:{line_number}", f"missing:{','.join(missing)}")
                )
                continue
            record = normalize_row(
                raw,
                source_file=resolved.name,
                dataset_class=dataset_class,
                version="adapter-0.9.0",
            )
            if record.label_scope not in {"sample", "unknown"}:
                excluded.append(ExcludedRow(record.source_record_id, "unsupported_label_scope"))
                continue
            records.append(record)
            samples.add(record.source_sample_id)
            if record.label.value:
                labels[str(record.label.value)] += 1
            splits[record.split] += 1
            types[record.event_type] += 1
    notes = "Normalized endpoint JSONL. Not enrolled-agent telemetry. Not Linux start_ticks."
    if dataset_class == "synthetic_endpoint_protocol":
        notes += " SYNTHETIC PROTOCOL FIXTURE. Not DMBD/WinMET/OpTC."
    manifest = EndpointManifest(
        name="dmbd_jsonl" if dataset_class == "external_endpoint_benchmark" else dataset_class,
        version="phase12-adapter-0.9.0",
        path=str(resolved),
        sha256=checksum,
        file_size_bytes=size,
        row_count=len(records),
        excluded_count=len(excluded),
        excluded_reasons=dict(Counter(item.reason.split(":")[0] for item in excluded)),
        sample_count=len(samples),
        label_counts=dict(labels),
        label_scope="sample",
        split_counts=dict(splits),
        event_types=dict(types),
        dataset_class=dataset_class,
        available=True,
        notes=notes,
    )
    return LoadedEndpoint(tuple(records), tuple(excluded), manifest)


def absent_manifest(reason: str) -> EndpointManifest:
    return EndpointManifest(
        name="dmbd",
        version="not_present",
        path="",
        sha256="",
        file_size_bytes=0,
        row_count=0,
        excluded_count=0,
        excluded_reasons={},
        sample_count=0,
        label_counts={},
        label_scope="sample",
        split_counts={},
        event_types={},
        dataset_class="external_endpoint_benchmark",
        available=False,
        notes=reason,
    )
